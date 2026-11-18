<p align="center">
  <img src="assets/badge.png" alt="The Viserion Claude Agent badge" width="120">
</p>

# claude-agent

Runs git and gh as the GitHub App `viserion-claude-agent`, so work done by an
agent shows as the App and not as an engineer. This is a tool for the pilot of
the Agent Identity and Human Approval proposal. It is not a standard, and
nothing here binds anyone until that proposal is adopted.

## Quick start

For an engineer who has finished [Setup](#setup) and whose project has the App
installed:

```
cd path/to/your-project
claude-agent launch -- claude
```

Work with Claude as you normally would. Anything it commits, pushes or opens
shows as `viserion-claude-agent[bot]`. When it opens a pull request, review it
in the browser and approve it **as yourself**. GitHub allows that because you
are not the author. The agent never approves or merges: a person does the
merge.

## Using it on your project

**Before you start**

- Run `claude-agent check`. It lists the repositories the App is installed on.
  If your project is not in the list, ask an organisation owner to install the
  App on it (see [For an organisation owner](#for-an-organisation-owner-once)).
- Start the session from your project's directory.

**Rules that matter**

- **Start the session with `launch`.** Commits, pushes and pull requests made
  from an ordinary terminal are yours, and GitHub will not let you approve your
  own.
- **Do not commit or push from another terminal while the session runs.** Same
  reason. If you need a change, ask the agent for it.
- **Sessions last an hour.** The token the session runs on expires, and later
  git and `gh` calls fail with `401`. Exit and run `launch` again. Your commits
  and branches are in git, so nothing is lost.
- **Limit what a session can reach with `--repo`.** The repository name is the
  bare name, without the organisation:
  `claude-agent launch --repo your-project -- claude`. Without `--repo` the
  token covers every repository the App is installed on.
- **If the latest commit came out as you,** you made it outside `launch`. Run
  `claude-agent launch -- git commit --amend --reset-author --no-edit` on that
  branch. If the branch was already pushed, push again from inside `launch`
  with `git push --force-with-lease`. For older commits, redo them inside
  `launch`.

**What you do as the human**

- Read the pull request and approve it in the browser. Your approval is the
  attributable sign-off.
- Merge it yourself. The App holds no approve or merge permission, and it must
  never be added to a ruleset's bypass list or a reviewer team.

## Troubleshooting

| What you see | What it means | What to do |
| --- | --- | --- |
| `no private key at …` or `… must have mode 600` | The key file is missing or too open. Read the first line. The lines after it (`401`, then `is not installed on westernmilling`) are noise from the failed key read, and the last one is misleading. | Put the key at `~/.config/claude-agent/app-key.pem` and run `chmod 600` on it. |
| `curl: (22) … 401` followed by `is not installed on westernmilling`, with no line before it about the key | The key is readable but GitHub rejects it: it belongs to a different App, or it was deleted. The "not installed" line is misleading here too. | Check with an organisation owner that the key was generated for `viserion-claude-agent` and still exists. |
| `curl: (22) … 422` from `check`, `token` or `launch` | A `--repo` name was refused: it is misspelled, or the App is not installed on it. | Run `claude-agent check` to see the valid names. |
| `Repository not found` from git, or `Could not resolve to a Repository` from `gh`, inside a session | The App is not installed on that repository. | Ask an organisation owner to install it. |
| `401` or `Bad credentials` in a session that has been running about an hour | The one-hour token expired. | Exit and run `launch` again. |
| `claude-agent: command not found` | The script is not on your `PATH`. | Redo step 3 of the engineer setup, and check `~/.local/bin` is on your `PATH`. |

## What `launch` does

```
claude-agent check                         # list the repositories the App can reach
claude-agent token [--repo NAME ...]       # print a one-hour installation token
claude-agent launch [--repo NAME ...] -- CMD...
```

`launch` runs `CMD` (usually `claude`) with:

- the App's token in `GH_TOKEN`, so `gh` acts as the App;
- git commits authored as `viserion-claude-agent[bot]`;
- SSH remotes rewritten to HTTPS, and git's credential helpers replaced by one
  that offers the App token to github.com only, so a push uses the App and not
  your SSH key or a helper configured in the repository;
- your SSH agent, your global git config (credential helpers, signing keys) and
  your `gh` login hidden from the session.

Your own shell is unchanged, and your repository's remote and config are not
edited. The scratch directory `launch` creates for `gh` is deleted when the
command exits.

## Setup

### For an organisation owner (once)

1. Install the App on the repositories that should use it, choosing "Only
   select repositories". Start with `engineering_practices`. The App already has
   the permissions the proposal asks for: contents and pull requests (write),
   checks, statuses and metadata (read). Do not add it to a ruleset's bypass
   list, and do not put it on a reviewer team.
2. For each engineer, generate a private key under the App's settings, Private
   keys. Every engineer has a separate key, and a key is never copied to anyone
   else (see [Keys](#keys)).
3. Pass the key to that engineer through an approved secret store (see
   [Configuration & Secrets](../../standards/08-configuration-secrets.md)),
   never chat or email.

### For an engineer (once)

1. Get **your own** key from an organisation owner. It is a secret: never
   commit it, and never paste it into a chat or an agent session.
2. Store it at `~/.config/claude-agent/app-key.pem` with mode 600, or set
   `CLAUDE_AGENT_APP_KEY_CMD` to a command that prints the key from a secret
   manager.
3. Put the script on your `PATH`:

   ```
   ln -s "$PWD/tools/claude-agent/scripts/claude-agent" ~/.local/bin/claude-agent
   ```

4. Check it: `claude-agent check` should list the installed repositories.

It needs `bash`, `openssl`, `curl`, `jq` and `git`. `gh` is needed only if the
session uses it.

## Keys

- **One key per engineer, never shared.** A key stays valid until it is
  deleted. It does not expire, and the one-hour limit applies only to the
  tokens made from it. Separate keys mean a lost laptop or someone leaving is
  handled by deleting one key without affecting anyone else, and no key has to
  be sent between people. GitHub allows several keys per App (up to 25,
  according to its documentation).
- **Revoke by deleting the key.** An owner deletes it under the App's settings,
  Private keys. Tokens already minted last at most an hour.
- **Rotate** by generating a new key, running `claude-agent check` with it, and
  then deleting the old one.
- **Fallback: one shared key in a secret manager.** If generating keys turns
  out to need an organisation owner every time, hold a single key in AWS
  Secrets Manager (see §8) and read it with `CLAUDE_AGENT_APP_KEY_CMD`. Nobody
  keeps a copy, access is controlled and audited through IAM, and removing
  someone's access plus rotating the key revokes them. This is not the default.
- **Not yet confirmed:** whether anyone other than an organisation owner can
  generate keys. Check the App's settings.

## Limits

- **Tokens last one hour.** A session that runs longer starts getting `401`
  errors. Relaunch it. Refreshing a token inside a running session is not
  built.
- **The key is as safe as where it is stored.** A key file is readable by any
  process running as you, and an agent session runs as you. Keeping the key in
  a secret manager that needs an unlock, or running agents as a separate user,
  would close that. Which to use is an open decision on the proposal.
- **This does not stop the App approving or merging.** That is the ruleset's
  job: see the proposal's ruleset settings.
- **The installation is found by organisation.** The script asks GitHub which
  installation of the App belongs to `westernmilling`. Set
  `CLAUDE_AGENT_INSTALLATION_ID` to skip that call.

## Settings

Only the key location needs setting:

| Variable | Default |
| --- | --- |
| `CLAUDE_AGENT_APP_KEY_FILE` | `~/.config/claude-agent/app-key.pem` |
| `CLAUDE_AGENT_APP_KEY_CMD` | none (a command that prints the key) |

The other settings have defaults and are described at the top of the script.

## Tests

```
bash tools/claude-agent/tests/test_claude_agent.sh
```

The tests use a throwaway key and a fake token. They need no network and touch
no real credentials.
