# Streamlit Cloud Deployment Guide

## Git LFS Configuration ✅

This repository uses **Git Large File Storage (LFS)** to track large files that exceed GitHub's 100 MB limit.

### Files Tracked with LFS:
- `monier_williams_concept_store.json` (108 MB) - Sanskrit-English dictionary for bilingual RAG support

### Deployment Requirements:

**For Streamlit Cloud:**

1. **packages.txt** - System-level dependencies installed first
   - Contains: `git-lfs` - Required to download LFS-tracked files during clone

2. **requirements.txt** - Python dependencies installed after packages

3. **.streamlit/config.toml** - Streamlit configuration

### How Streamlit Cloud Handles LFS:

1. When you deploy to Streamlit Cloud, it reads `packages.txt`
2. Installs system packages (like `git-lfs`) at OS level
3. Clones your GitHub repository with `git lfs pull`
4. This retrieves LFS-tracked files (not just pointers)
5. Python dependencies are installed from `requirements.txt`

### For Local Development:

```bash
# Install Git LFS
brew install git-lfs  # macOS
apt-get install git-lfs  # Linux
choco install git-lfs  # Windows

# Initialize LFS (one-time)
git lfs install

# Clone/pull repository
git clone https://github.com/stewari1210/Vedic-Sanskrit-Tutor.git
cd Vedic-Sanskrit-Tutor
git lfs pull  # Downloads LFS-tracked files
```

### Verifying LFS Setup:

```bash
# Check what files are tracked with LFS
git lfs ls-files

# Output should show:
# 3b6467ea50 * monier_williams_concept_store.json
```

### Benefits:

✅ MW dictionary available in cloud Streamlit  
✅ Bilingual Sanskrit query support on cloud  
✅ No need to upload 108MB file in git history  
✅ Stays under GitHub's repository size limits  
✅ Same functionality as local deployment  

---

**Questions?** See: https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage
