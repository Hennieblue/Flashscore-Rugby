FLASHSCORE RUGBY TODAY - GITHUB PAGES
=====================================

Create a PUBLIC GitHub repository named: Flashscore-Today

Upload these five files first:
README.txt
requirements.txt
update_flashscore.py
data.json
index.html

Then create a new file on GitHub with this exact filename:
.github/workflows/pages.yml

Paste the contents of the included .github/workflows/pages.yml into that file
and commit it.

In repository Settings, Pages, Build and deployment, set Source to GitHub
Actions. Open Actions and manually run Update Flashscore Rugby the first time.

When successful, the address will be:
https://hennieblue.github.io/Flashscore-Today/

The phone page checks for fresh data every 30 seconds. GitHub normally updates
the Flashscore data about every 5 minutes. Flashscore may sometimes block an
automated Chrome session. Check the GitHub Actions result if the page is empty.
