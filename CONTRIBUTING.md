# Git guide for the team

Git only needs about six commands for this weekend.

## The idea

- The repo on GitHub is the shared copy. Each person has their own copy on their laptop.
- **Commit** saves a snapshot locally. **Push** sends it to GitHub. **Pull** gets everyone else's changes.

## First time only

```bash
git clone https://github.com/phonehseng/mlhhackathonbacteriagang
cd mlhhackathonbacteriagang
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Sign in to GitHub with a [personal access token](https://github.com/settings/tokens) (tick **repo**) or an SSH key. Passwords don't work.

## The daily loop

```bash
git pull                          # 1. get the latest first
# ...edit files...
git add -A                        # 2. stage your changes
git commit -m "what you did"      # 3. save a snapshot
git pull                          # 4. grab anything new again
git push                          # 5. send it to GitHub
```

`git status` shows what has changed at any time.

## Habits that prevent most problems

- Pull before you start working, and before you push.
- Commit small and often, with a short message like "add upload page".
- Avoid editing the same file at the same time as someone else. Split work by file or folder.
- For bigger changes, use a branch: `git checkout -b my-feature`, then `git push -u origin my-feature`. Merge to `main` with a pull request on GitHub.
- Never commit secrets. API keys and passwords go in `.env`, which is gitignored.

## Common errors

- **"rejected... fetch first"**: someone pushed before you. Run `git pull`, then `git push` again.
- **Merge conflict**: git marks the clashing lines with `<<<<<<<` and `>>>>>>>`. Keep the version you want, delete the markers, then `git add -A` and `git commit`. Ask a teammate if unsure.
- **"Authentication failed"**: use a token or SSH key, not your password.
- **Nothing happens on push**: you probably forgot to `git commit` first.

## Prefer no terminal?

[GitHub Desktop](https://desktop.github.com) gives a point-and-click version of the same loop (Fetch/Pull, Commit, Push).
