# HydroRisk Git Workflow Guide

## Problem: Why Keep Getting Merge Conflicts?

You keep encountering diverged branches because:

1. **You make local commits** (e.g., "flood history fix")
2. **Remote has updates** from collaborators
3. **Your branches diverge** — you need a merge to reconcile them

### Example:
```
Local:    ... → ecdb99c → 913b0a3 (flood history fix)
                    ↓
Remote:   ... → ecdb99c → 8c9786f (accumulation model)

Result: Diverged branches requiring merge
```

---

## ✅ THE CORRECT WORKFLOW

### Option 1: Always Pull Before Pushing (Recommended)

**BEFORE you make changes:**
```bash
git pull HydroRisk master
```

**Then make your changes and commit:**
```bash
git add .
git commit -m "Your descriptive message"
```

**Finally push:**
```bash
git push HydroRisk master
```

This ensures you have the latest remote code before working locally.

### Option 2: Pull with Rebase (Cleaner History)

If you've already made local commits and want to avoid merge commits:

```bash
git pull --rebase HydroRisk master
```

Then push:
```bash
git push HydroRisk master
```

---

## 🚫 WHAT NOT TO DO

❌ **DON'T:** Make commits and push without pulling first
```bash
# Bad workflow:
git commit -m "my changes"
git push HydroRisk master  # ← Fails if remote has updates
```

❌ **DON'T:** Work on master directly with multiple people
- Create a feature branch instead
- Much safer for team projects

---

## 🛠️ RECOMMENDED: Feature Branch Workflow

If you're collaborating with others (Person 1 and Person 2):

### For each feature:
```bash
# 1. Update master
git checkout master
git pull HydroRisk master

# 2. Create feature branch
git checkout -b feature/flood-history-improvements

# 3. Make changes and commit (as many commits as you want)
git add .
git commit -m "Add SAR analysis improvements"
git commit -m "Improve flood detection logic"

# 4. Before pushing, pull latest master
git pull --rebase HydroRisk master

# 5. Push your feature branch
git push HydroRisk feature/flood-history-improvements

# 6. On GitHub, create a Pull Request (PR) for review
```

**Benefits:**
- No diverged branches
- Code review before merging
- Easy to abandon if needed
- Clear history of who changed what

---

## 🔧 QUICK FIX if You're in a Diverged State

If you end up with diverged branches again:

```bash
# Option A: Rebase your commits on top of remote (cleaner)
git pull --rebase HydroRisk master
git push HydroRisk master

# Option B: Merge remote into yours (creates merge commit)
git pull HydroRisk master
git push HydroRisk master

# Option C: Abort and start fresh (nuclear option)
git merge --abort
git fetch HydroRisk
git reset --hard HydroRisk/master
```

---

## 📋 Current Status Check

To see if you're in sync:

```bash
# Check if you're ahead, behind, or diverged
git status

# See local vs remote branches
git log --oneline -5 master
git log --oneline -5 HydroRisk/master

# See what's different
git diff master HydroRisk/master
```

---

## 🎯 BEST PRACTICE GOING FORWARD

1. **Every day before starting work:**
   ```bash
   git pull HydroRisk master
   ```

2. **Make your changes** in a feature branch or on master

3. **Before pushing:**
   ```bash
   git pull --rebase HydroRisk master  # Get latest updates
   git push HydroRisk master
   ```

4. **If there are conflicts during rebase:**
   - Git will tell you which files conflict
   - Fix the conflicts in your editor
   - `git add <file>`
   - `git rebase --continue`
   - `git push HydroRisk master`

---

## Summary Table

| Scenario | Command | Why |
|----------|---------|-----|
| **Before starting work** | `git pull HydroRisk master` | Get latest code |
| **After making changes** | `git add .` and `git commit` | Save your work |
| **Before pushing** | `git pull --rebase HydroRisk master` | Avoid divergence |
| **Push to remote** | `git push HydroRisk master` | Share your changes |
| **Undo last commit** | `git reset --soft HEAD~1` | Keep changes, undo commit |
| **Undo last push** | `git reset --hard HEAD~1` and `git push -f` | Only if not shared! |


