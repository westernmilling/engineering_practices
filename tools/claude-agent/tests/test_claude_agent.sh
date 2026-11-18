#!/usr/bin/env bash
# Tests for scripts/claude-agent. No network and no real credentials: a throwaway
# key signs the JWT, and `launch` runs with a fake token and bot id.
set -uo pipefail

here=$(cd "$(dirname "$0")" && pwd)
script=$here/../scripts/claude-agent
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# Start clean: an engineer's own settings, such as a key command for a secret
# manager, must not reach the tests or sign anything.
for name in $(compgen -v CLAUDE_AGENT_); do unset "$name"; done
failures=0

pass() { echo "ok   $1"; }
fail() { echo "FAIL $1"; failures=$((failures + 1)); }
check() { if [ "$2" = "$3" ]; then pass "$1"; else fail "$1 (expected [$3], got [$2])"; fi; }

dec() {
  local x
  x=$(printf '%s' "$1" | tr '_-' '/+')
  while [ $(( ${#x} % 4 )) -ne 0 ]; do x="$x="; done
  printf '%s' "$x" | base64 -d
}

openssl genrsa -out "$tmp/key.pem" 2048 2>/dev/null
chmod 600 "$tmp/key.pem"
openssl rsa -in "$tmp/key.pem" -pubout -out "$tmp/pub.pem" 2>/dev/null
export CLAUDE_AGENT_APP_KEY_FILE=$tmp/key.pem

# JWT
jwt=$("$script" jwt)
IFS=. read -r header payload signature <<<"$jwt"
check "jwt header" "$(dec "$header")" '{"alg":"RS256","typ":"JWT"}'
check "jwt issuer is the app id" "$(dec "$payload" | jq -r .iss)" 5240375
lifetime=$(dec "$payload" | jq -r '.exp - .iat')
if [ "$lifetime" -le 600 ]; then pass "jwt lifetime is at most 10 minutes"; else fail "jwt lifetime is $lifetime seconds"; fi
dec "$signature" > "$tmp/sig.bin"
if printf '%s.%s' "$header" "$payload" | openssl dgst -sha256 -verify "$tmp/pub.pem" -signature "$tmp/sig.bin" >/dev/null; then
  pass "jwt signature verifies"
else
  fail "jwt signature does not verify"
fi

# Key handling
chmod 644 "$tmp/key.pem"
if "$script" jwt >/dev/null 2>&1; then fail "a key that is not mode 600 is refused"; else pass "a key that is not mode 600 is refused"; fi
chmod 600 "$tmp/key.pem"
if CLAUDE_AGENT_APP_KEY_FILE=$tmp/missing.pem "$script" jwt >/dev/null 2>&1; then fail "a missing key is refused"; else pass "a missing key is refused"; fi
check "a key can come from a command" "$(CLAUDE_AGENT_APP_KEY_FILE=$tmp/missing.pem CLAUDE_AGENT_APP_KEY_CMD="cat $tmp/key.pem" "$script" jwt | cut -d. -f1)" "$header"

# launch: a repository whose remote is SSH, and a global git config with an identity
git init -q "$tmp/repo"
git -C "$tmp/repo" remote add origin git@github.com:westernmilling/example.git
printf '[user]\n\tname = Some Engineer\n\temail = engineer@example.com\n' > "$tmp/gitconfig"
export GIT_CONFIG_GLOBAL=$tmp/gitconfig CLAUDE_AGENT_TEST_TOKEN=ghs_TEST CLAUDE_AGENT_BOT_ID=123
export SSH_AUTH_SOCK=$tmp/agent.sock

run() { (cd "$tmp/repo" && "$script" launch -- "$@"); }

check "launch sets GH_TOKEN" "$(run bash -c 'echo $GH_TOKEN')" ghs_TEST
check "launch drops the ssh agent" "$(run bash -c 'echo "[${SSH_AUTH_SOCK:-}]"')" "[]"
check "launch authors commits as the app" \
  "$(run bash -c 'git var GIT_AUTHOR_IDENT' | cut -d' ' -f1-2)" "viserion-claude-agent[bot] <123+viserion-claude-agent[bot]@users.noreply.github.com>"
check "launch ignores the engineer's git identity" "$(run bash -c 'git config user.name || true')" ""
check "launch sends ssh remotes over https" "$(run git ls-remote --get-url origin)" https://github.com/westernmilling/example.git
check "git gets the app token as its password" \
  "$(run bash -c 'printf "protocol=https\nhost=github.com\n\n" | git credential fill' | grep '^password=')" password=ghs_TEST
check "gh has no stored login of its own" "$(run bash -c 'ls "$GH_CONFIG_DIR" 2>/dev/null | wc -l | tr -d " "')" 0
check "launch passes the exit status through" "$(run bash -c 'exit 7'; echo $?)" 7
check "the App helper answers only for github.com" \
  "$(run bash -c 'printf "protocol=https\nhost=example.org\n\n" | git credential fill 2>/dev/null | grep -c "^password="')" 0
git -C "$tmp/repo" config --local credential.helper '!f() { echo username=engineer; echo password=ENGINEER_SECRET; }; f'
check "a repo-local credential helper cannot answer for the engineer" \
  "$(run bash -c 'printf "protocol=https\nhost=github.com\n\n" | git credential fill' | grep '^password=')" password=ghs_TEST
git -C "$tmp/repo" config --local --unset credential.helper
check "the caller's environment is untouched" "$(git config --global user.name)" "Some Engineer"

# check: follows pages. A stand-in curl serves a full first page, a short second page
# and then an empty one.
mkdir -p "$tmp/bin"
cat > "$tmp/bin/curl" <<'STUB'
#!/usr/bin/env bash
for arg in "$@"; do
  case $arg in
    *"&page=1") jq -nc '{repositories: [range(100) | {full_name: "org/repo\(.)"}]}'; exit 0 ;;
    *"&page=2") jq -nc '{repositories: [range(3) | {full_name: "org/extra\(.)"}]}'; exit 0 ;;
    *"&page=3") jq -nc '{repositories: []}'; exit 0 ;;
  esac
done
exit 22
STUB
chmod +x "$tmp/bin/curl"
check "check lists every page of repositories" "$(PATH=$tmp/bin:$PATH timeout 10 "$script" check | head -n 1000 | wc -l | tr -d ' ')" 103

if [ "$failures" -gt 0 ]; then echo "$failures failed"; exit 1; fi
echo "all passed"
