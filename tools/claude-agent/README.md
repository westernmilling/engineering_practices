# claude-agent

Runs git and gh as the GitHub App `viserion-claude-agent`, so work done by an
agent shows as the App and not as an engineer. This is a tool for the pilot of
the Agent Identity and Human Approval proposal. It is not a standard, and
nothing here binds anyone until that proposal is adopted.

## What it does

```
claude-agent check                         # list the repositories the App can reach
claude-agent token [--repo NAME ...]       # print a one-hour installation token
claude-agent launch [--repo NAME ...] -- CMD...
```

`launch` runs `CMD` (for example `claude`) with:

- the App's token in `GH_TOKEN`, so `gh` acts as the App;
- git commits authored as `viserion-claude-agent[bot]`;
- SSH remotes rewritten to HTTPS, and git's credential helpers replaced by one
  that offers the App token to github.com only, so a push uses the App and not
  your SSH key or a helper configured in the repository;
- your SSH agent, your global git config (credential helpers, signing keys) and
  your `gh` login hidden from the session.

Your own shell is unchanged. The scratch directory `launch` creates for `gh` is
deleted when the command exits.

## Setup

**Once, by an organisation owner.** Install the App on the repositories that
should use it, choosing "Only select repositories". Start with
`engineering_practices`. The App already has the permissions the proposal
asks for: contents and pull requests (write), checks, statuses and metadata
(read). Do not add it to a ruleset's bypass list, and do not put it on a
reviewer team.

**Once per engineer.**

1. Get **your own** private key for the App. An organisation owner generates
   it under the App's settings, Private keys, and hands it to you. Every
   engineer has a separate key, and a key is never copied to anyone else (see
   [Keys](#keys)). The key is a secret (see
   [Configuration & Secrets](../../standards/08-configuration-secrets.md)): never
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
