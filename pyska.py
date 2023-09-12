import re
import subprocess
from contextlib import contextmanager
from pprint import pformat

import requests
import sublime
import sublime_plugin
import yaml

reg = re.compile(r"def (.+)\(")


class PyskaCommand(sublime_plugin.TextCommand):
    @contextmanager
    def booga(self):
        try:
            self.window = self.view.window()
            self.window.destroy_output_panel("my_output_panel")
            self.output_panel = self.window.create_output_panel("my_output_panel")
            self.output_panel.set_name("My Output Panel")
            self.output_panel.set_syntax_file(
                "Packages/ShellScript/Shell-Unix-Generic.sublime-syntax"
            )
            self.window.run_command("show_panel", {"panel": "output.my_output_panel"})
            yield self.output_panel
        except Exception as e:
            sublime.message_dialog(str(e))

    def run_process(self):
        self.process = subprocess.Popen(
            self.composite_command,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    def print(self, text):
        self.output_panel.run_command("append", {"characters": text})

    @property
    def pre(self):
        return sublime.active_window().project_data().get("pyska", dict()).get("commands", [])

    @property
    def args(self):
        args = sublime.active_window().project_data().get("pyska", dict()).get("args", None)
        if args:
            return " %s" % args
        return ""

    def run(self, edit):
        with self.booga():
            folder = (
                sublime.active_window().project_data()["folders"][0]["path"].replace(" ", "\\ ")
            )
            filename = self.view.file_name()
            test_name = self.get_test_name()
            if test_name:
                test_name = "::%s" % test_name
            else:
                test_name = ""

            commands = (
                ["cd %s" % folder]
                + self.pre
                + ["poetry run pytest%s %s%s" % (self.args, filename, test_name)]
            )
            self.print("NEW one\n")
            for command in commands:
                self.print("%s\n" % command)
            self.composite_command = " && ".join(commands)
            sublime.set_timeout_async(self.run_process)
            sublime.set_timeout_async(self.ared, 0.001)

    def ared(self):
        line = self.process.stdout.readline().decode()
        self.print(line)
        self.keep_on_track()
        if not (not line and self.process.poll() is not None):
            sublime.set_timeout_async(self.ared, 0)
        else:
            self.process.terminate()

    def keep_on_track(self):
        self.output_panel.run_command(
            "goto_line", {"line": self.output_panel.rowcol(self.output_panel.size())[0] + 1}
        )

    def get_test_name(self):
        cursor_position = self.view.sel()[0].begin()
        top_level_string = self.get_top_level_string(cursor_position)
        try:
            return reg.findall(top_level_string)[0]
        except IndexError:
            return None

    def get_top_level_string(self, cursor_position):
        region = self.view.line(cursor_position)
        while not self.view.match_selector(region.begin(), "meta.function"):
            if region.begin() == 0:
                break
            region = self.view.line(region.begin() - 1)
        return self.view.substr(region).strip()


class ShowPyskaCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.window().run_command("show_panel", {"panel": "output.my_output_panel"})


class LipStickCommand(sublime_plugin.TextCommand):
    @property
    def url(self):
        return "http://127.0.0.1:9200/_search"

    def get_result(self) -> str:
        # Parse YAML into a Python dictionary
        yaml_data = self.view.substr(sublime.Region(0, self.view.size()))
        try:
            parsed_dict = yaml.safe_load(yaml_data)
        except Exception:
            return "Not yaml 😞"
        else:
            res = requests.get(self.url, json=parsed_dict).json()
            return pformat(res)

    def run(self, edit):
        # Get the content you want to write to the view
        # Convert the JSON content to a string
        # json_string = json.dumps(self.get_result(), indent=4)
        json_string = self.get_result()

        # Create a new view
        new_view = self.view.window().new_file()

        # Set the syntax to JSON
        # new_view.set_syntax_file("Packages/JavaScript/JSON.sublime-syntax")
        new_view.set_syntax_file("Packages/Python/python.sublime-syntax")

        # Set the content of the new view
        new_view.insert(edit, 0, json_string)

        # Set the scratch flag to true to indicate it's a temporary view
        new_view.set_scratch(True)

        # Focus on the newly created view
        self.view.window().focus_view(new_view)
