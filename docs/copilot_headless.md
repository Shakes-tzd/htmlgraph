Programmatic mode: You can also pass the CLI a single prompt directly on the command line. You do this by using the -p or --prompt command-line option. To allow Copilot to modify and execute files you should also use one of the approval options (see Allowing tools to be used without manual approval later in this article). For example:

Bash
copilot -p "Show me this week's commits and summarize them" --allow-tool 'shell(git)'
Alternatively, you can use a script to output command-line options and pipe this to copilot. For example:

Bash
echo ./script-outputting-options.sh | copilot
Caution

If you use an automatic approval option such as --allow-all-tools, Copilot has the same access as you do to files on your computer, and can run any shell commands that you can run, without getting your prior approval. See Security considerations, later in this article.
Use cases for GitHub Copilot CLI

The following sections provide examples of tasks you can complete with GitHub Copilot CLI.

Local tasks

From within a project directory you can ask Copilot to make a change to the code in the project. For example:

Change the background-color of H1 headings to dark blue

Copilot finds the CSS file where H1 headings are defined and changes the color value.

Ask Copilot to tell you about changes to a file:

Show me the last 5 changes made to the CHANGELOG.md file. Who changed the file, when, and give a brief summary of the changes they made

Use Copilot to help you improve the code, or documentation, in your project.

Suggest improvements to content.js

Rewrite the readme in this project to make it more accessible to newcomers

Use Copilot to help you perform Git operations.

Commit the changes to this repo

Revert the last commit, leaving the changes unstaged

Ask Copilot to create an application from scratch—for example, as a proof of concept.

Use the create-next-app kit and tailwind CSS to create a next.js app. The app should be a dashboard built with data from the GitHub API. It should track this project's build success rate, average build duration, number of failed builds, and automated test pass rate. After creating the app, give me easy to follow instructions on how to build, run, and view the app in my browser.

Ask Copilot to explain why a change it made is not working as expected, or tell Copilot to fix a problem with the last change it made. For example:

You said: "The application is now running on http://localhost:3002 and is fully functional!" but when I browse to that URL I get "This site can't be reached"

Tasks involving GitHub.com

Fetch and display details about your work from GitHub.com.

List my open PRs

This lists your open pull requests from any repository on GitHub. For more specific results, include the repository name in your prompt:

List all open issues assigned to me in OWNER/REPO

Ask Copilot to work on an issue:

I've been assigned this issue: https://github.com/octo-org/octo-repo/issues/1234. Start working on this for me in a suitably named branch.

Ask Copilot to make file changes and raise a pull request on GitHub.com.

In the root of this repo, add a Node script called user-info.js that outputs information about the user who ran the script. Create a pull request to add this file to the repo on GitHub.

Create a PR that updates the README at https://github.com/octo-org/octo-repo, changing the subheading "How to run" to "Example usage"

Copilot creates a pull request on GitHub.com, on your behalf. You are marked as the pull request author.

Ask Copilot to create an issue for you on GitHub.com.

Raise an improvement issue in octo-org/octo-repo. In src/someapp/somefile.py the `file = open('data.txt', 'r')` block opens a file but never closes it.

Ask Copilot to check the code changes in a pull request.

Check the changes made in PR https://github.com/octo-org/octo-repo/pull/57575. Report any serious errors you find in these changes.

Copilot responds in the CLI with a summary of any problems it finds.

Manage pull requests from GitHub Copilot CLI.

Merge all of the open PRs that I've created in octo-org/octo-repo

Close PR #11 on octo-org/octo-repo

Find specific types of issues.

Use the GitHub MCP server to find good first issues for a new team member to work on from octo-org/octo-repo

Note

If you know that a specific MCP server can achieve a particular task, then specifying it in your prompt can help Copilot to deliver the results you want.
Find specific GitHub Actions workflows.

List any Actions workflows in this repo that add comments to PRs

Create a GitHub Actions workflow.

Branch off from main and create a GitHub Actions workflow that will run on pull requests, or can be run manually. The workflow should run eslint to check for problems in the changes made in the PR. If warnings or errors are found these should be shown as messages in the diff view of the PR. I want to prevent code with errors from being merged into main so, if any errors are found, the workflow should cause the PR check to fail. Push the new branch and create a pull request.

Customizing GitHub Copilot CLI

You can customize GitHub Copilot CLI in a number of ways:

Custom instructions: Custom instructions allow you to give Copilot additional context on your project and how to build, test and validate its changes. For more information, see Using GitHub Copilot CLI.
Model Context Protocol (MCP) servers: MCP servers allow you to give Copilot access to different data sources and tools. For more information, see Using GitHub Copilot CLI.
Custom agents: Custom agents allow you to create different specialized versions of Copilot for different tasks. For example, you could customize Copilot to be an expert frontend engineer following your team's guidelines. For more information, see Using GitHub Copilot CLI.
Skills: Skills allow you to enhance the ability of Copilot to perform specialized tasks with instructions, scripts, and resources. For more information, see About Agent Skills.