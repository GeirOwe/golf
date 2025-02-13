# Deployment Guide

## Render.com Deployment
1. Push code to GitHub
2. Connect to Render.com
3. Create new Web Service
4. Configure:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Environment Variables:
     ```
     FLASK_APP=app.py
     FLASK_ENV=production
     DATA_DIR=/opt/render/project/src/data
     ```

## Notes
- Free tier will spin down with inactivity
- Initial load may take ~30 seconds
- Data persists in JSON files