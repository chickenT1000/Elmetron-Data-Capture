# Git Repository Cleanup - Remove Large Database Files

## Problem
Repository is >100 MB because database files were committed in the past:
- data/elmetron.sqlite (100 MB)
- data/elmetron.sqlite-wal (multiple 4-6 MB files)
- data/elmetron.sqlite.corrupted (96 MB)

These are now in .gitignore but still in git history.

## Solution: Clean Git History

### Option 1: Using git filter-repo (Best)

1. **Install git-filter-repo:**
```bash
pip install git-filter-repo
```

2. **Backup your branch:**
```bash
git branch backup-before-cleanup
```

3. **Remove large files from ALL commits:**
```bash
cd C:\Users\EKO\Desktop\GitHub\Elmetron-Data-Capture

git filter-repo --path data/elmetron.sqlite --invert-paths
git filter-repo --path data/elmetron.sqlite-wal --invert-paths  
git filter-repo --path data/elmetron.sqlite-shm --invert-paths
git filter-repo --path data/elmetron.sqlite.corrupted.20250930_143523 --invert-paths
git filter-repo --path data/live_rehearsal_ui.sqlite --invert-paths
```

4. **Force push (if already pushed to remote):**
```bash
git push origin --force --all
```

### Option 2: Using BFG Repo-Cleaner

1. **Download BFG:**
   - Get from: https://rtyley.github.io/bfg-repo-cleaner/
   - Requires Java

2. **Run BFG:**
```bash
java -jar bfg.jar --delete-files "elmetron.sqlite" .
java -jar bfg.jar --delete-files "*.sqlite-wal" .
java -jar bfg.jar --delete-files "*.corrupted*" .
```

3. **Clean up:**
```bash
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

### Option 3: Start Fresh (Nuclear Option)

If the history isn't important:

1. **Create new repo:**
```bash
cd ..
mv Elmetron-Data-Capture Elmetron-Data-Capture.old
mkdir Elmetron-Data-Capture
cd Elmetron-Data-Capture
git init
```

2. **Copy only source files (not data/):**
```bash
xcopy /E /I ..\Elmetron-Data-Capture.old\elmetron elmetron
xcopy /E /I ..\Elmetron-Data-Capture.old\ui ui
copy ..\Elmetron-Data-Capture.old\.gitignore .
# ... copy other source files
```

3. **Make initial commit:**
```bash
git add -A
git commit -m "Initial commit - clean history"
```

## Quick Fix (Doesn't clean history)

If you just want to commit current changes:

```bash
# Stage all changes (including deletions of database files)
git add -A

# Commit
git commit -m "feat: Session overlay redesign + marker precision fix

- Added DELETE /api/sessions/<id> endpoint
- Rounded marker offsets to whole seconds (device is 1 Hz)
- Updated frontend marker display to mm:ss format
- Fixed marker dialog showing decimal minutes
- Analysis: CX-505 sends 1 Hz data, no sub-second precision exists"

# Push
git push
```

**Warning:** Repo will still be >100 MB. GitHub might reject it.

## Recommended: Update .gitignore First

Add to .gitignore to prevent future issues:

```gitignore
# Database files - ALL VARIANTS
data/*.sqlite*
data/*.db*
*.corrupted*
*.corrupted

# Make sure data directory itself allows .gitkeep
!data/.gitkeep
```

## After Cleanup

1. Verify repo size:
```bash
git count-objects -vH
```

2. Check that files are gone:
```bash
git log --all --full-history -- data/elmetron.sqlite
# Should show nothing
```

3. Push cleaned history:
```bash
git push origin --force --all
git push origin --force --tags
```

## Prevention

Add to CI/CD or pre-commit hook:
```bash
# Check for large files before commit
git diff --cached --name-only | xargs -I {} sh -c '[ -f "{}" ] && [ $(wc -c < "{}") -gt 1048576 ] && echo "Error: {} is larger than 1MB"'
```
