# Git Upload Guide

This project includes a simple workflow for uploading your code to GitHub using Git.

## 1. Initialize Git

```bash
git init
```

## 2. Check the status

```bash
git status
```

## 3. Add files to staging

```bash
git add .
```

## 4. Commit your changes

```bash
git commit -m "Initial commit"
```

## 5. Create a GitHub repository

Go to GitHub and create a new repository. Do not initialize it with a README if you already have files in your local project.

## 6. Connect your local repo to GitHub

```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
```

## 7. Push to GitHub

```bash
git branch -M main
git push -u origin main
```

## 8. Future updates

After making new changes:

```bash
git add .
git commit -m "Your message"
git push
```

## Useful commands

```bash
git log
git pull
git checkout -b branch-name
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
```

## Notes

- Replace `YOUR_USERNAME` and `YOUR_REPOSITORY` with your actual GitHub username and repository name.
- If you already have a remote configured, use:

```bash
git remote set-url origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
```

- If Git asks for authentication, use your GitHub username and a personal access token.
