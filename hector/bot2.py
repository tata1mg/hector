import json
import os

from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from rich.panel import Panel
from rich.pretty import Pretty

from .client import APIClient
from .console import console
from .log import bot_logger
from .models import CovReport, DiffCovReport


class CoverageBot:
    def __init__(self, returncode: Union[int, str], cov: Optional[CovReport]=None, diff_cov: Optional[DiffCovReport]=None):
        self.returncode = int(returncode)
        self.client = APIClient()
        if not diff_cov or not cov:
            diff_cov, cov = self._parse_reports()
        self.diff_cov = diff_cov
        self.cov = cov

    def post(
        self,
        dry: Optional[bool] =  False
    ):
        with console.status("Preparing Comment"):
            bot_comment = self.get_comment()
            console.rule("Comment")
            console.log(Panel(bot_comment))

        if dry:
            return

        with console.status("Posting Comment", spinner="aesthetic"):
            self.post_comment(comment=bot_comment)

    def _parse_reports(self):
        if not os.path.isfile("diff-coverage.json"):
            raise Exception("Missing diff-coverage.json!")

        if not os.path.isfile("coverage.json"):
            raise Exception("Please provide a coverage.json file!")

        with console.status("Parsing Reports"):
            with open("diff-coverage.json", encoding="utf-8") as f:
                diff_cov = DiffCovReport(**json.load(f))

            with open("coverage.json", encoding="utf-8") as f:
                cov = CovReport(**json.load(f))
        return diff_cov, cov

    def get_comment(self):
        return self._format_comment()

    def _format_comment(self):
        comment = ""

        overall_coverage = self.cov.overall_coverage

        diff_coverage = self.diff_cov.diff_coverage
        lines_covered = self.diff_cov.lines_covered
        lines_missed = self.diff_cov.lines_missed

        # add title
        emoji = self._title_emoji()
        comment += f"## 📈 Diff Coverage `{diff_coverage:.2f}% {emoji}` \n\n"
        # add subtitle
        comment += f"##### Covered Lines `{lines_covered}` | Missing `{lines_missed}` | Overall Coverage `{overall_coverage:.2f}%` \n\n"

        # add file stats
        if lines_missed != 0:
            comment += "#### `📂 Missing Coverage` \n\n"
            file_stats = self._format_file_stats()
            comment += file_stats

        # add footer
        commit_link = self._format_commit_link()
        timestamp = self.timestamp()
        comment += f"###### 📝 Reported on commit {commit_link} | {timestamp})"
        return comment

    def _title_emoji(self):
        if self.returncode!=0:
            return "❗️"
        return "✅"

    def _format_file_stats(self):
        src_stats = self.diff_cov.src_stats
        file_stats = ["```sh"]
        for file, stat in src_stats.items():
            if stat["percent_covered"] < 100:
                file_stat = f"❗️ {stat['percent_covered']:5.2f}% | {file} {self.__convert_to_ranges(stat['violation_lines'])}"
                # console.log(file_stat)
                file_stats.append(file_stat)
        file_stats_len = len(file_stats)
        if file_stats_len > 10:
            file_stats = file_stats[:10]
        file_stats.append("```")
        step_link = f"https://bitbucket.org/{os.environ.get('BITBUCKET_WORKSPACE')}/{os.environ.get('BITBUCKET_REPO_SLUG')}/pipelines/results/{os.environ.get('BITBUCKET_PIPELINE_UUID')}/steps/{os.environ.get('BITBUCKET_STEP_UUID')}"
        if file_stats_len > 10:
            file_stats.append(
                f"> *{file_stats_len - 10} more files [Full Coverage Report]({step_link})* \n\n"
            )
        else:
            file_stats.append(
                f"> *Check [Full Coverage Report]({step_link})* \n\n"
            )
        return "\n".join(file_stats)

    def _format_commit_link(self):
        commit_link = f"https://bitbucket.org/{os.environ.get('BITBUCKET_WORKSPACE')}/{os.environ.get('BITBUCKET_REPO_SLUG')}/commits/{os.environ.get('BITBUCKET_COMMIT')}"
        commit_link = f"[{commit_link}]({commit_link})"
        commit_link += "{: data-inline-card='' }"
        return commit_link

    def timestamp(self):
        return datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime(
            "%I:%M %p %Z, %A, %d %B %Y"
        )

    def post_comment(self, comment: str):
        repo_slug = os.environ.get("BITBUCKET_REPO_SLUG")
        pr_id = os.environ.get("BITBUCKET_PR_ID")
        url = f"https://api.bitbucket.org/2.0/repositories/{os.environ.get('BITBUCKET_WORKSPACE')}/{repo_slug}/pullrequests/{pr_id}/comments"
        console.log(f"POST url: {url}")
        headers = {
            "Authorization": f"Bearer {os.environ.get('TEST_COVERAGE_TOKEN')}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = json.dumps({"content": {"raw": comment}})
        resp = self.client.post(url, headers=headers, data=payload)
        console.rule("[DEBUG] API Response")
        console.log(f"Response Status {resp.status_code}")
        console.log(Panel(Pretty(resp.json())))

    @staticmethod
    def __convert_to_ranges(lst: list):
        if not lst:
            return ""
        ranges = []
        start = end = lst[0]
        for num in lst[1:]:
            if num == end + 1:
                end = num
            else:
                ranges.append(f"{start}-{end}" if start != end else str(start))
                start = end = num
        ranges.append(f"{start}-{end}" if start != end else str(start))
        return ", ".join(ranges)


if __name__ == "__main__":
    # FIXME: remove once cli stable
    with open("diff-coverage.json", encoding="utf-8") as f:
        diff_cov = DiffCovReport(**json.load(f))

    with open("coverage.json", encoding="utf-8") as f:
        cov = CovReport(**json.load(f))

    bot = CoverageBot(cov=cov, diff_cov=diff_cov)

    bot_comment = bot.get_comment()
    bot_logger.info(bot_comment)
    bot.post_comment(comment=bot_comment)
