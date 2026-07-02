# 🚀 AFROTC 695 Vercel Deployment Guide

This guide provides step-by-step instructions for deploying the AFROTC 695 Recruitment System to Vercel using Neon PostgreSQL and Vercel Blob storage.

## 📋 Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **GitHub/GitLab Repository**: Your code must be in a Git repository
3. **Neon PostgreSQL Database**: Already configured
4. **Vercel Blob Storage**: Already configured
5. **Environment Variables**: Ready to configure

## 🔧 Project Configuration

### Vercel Project ID
- **Project ID**: `prj_Dp0OjBia3YoTgbCxwQdkKr6BSSIz`
- **Project Name**: AFROTC 695 Recruitment System

### Required Files

1. **`vercel.json`**: Configuration for Vercel deployment
2. **`api/app.py`**: Flask application for serverless deployment
3. **`requirements.txt`**: Python dependencies
4. **`static/`**: Static assets (CSS, JS, images)
5. **`templates/`**: HTML templates

## 🚀 Deployment Steps

### Step 1: Connect Repository to Vercel

1. **Login to Vercel Dashboard**
   - Go to [vercel.com/dashboard](https://vercel.com/dashboard)
   - Sign in with your account

2. **Import Project**
   - Click "New Project"
   - Connect your Git repository (GitHub/GitLab)
   - Select the repository containing your AFROTC 695 code

3. **Configure Project Settings**
   - **Project Name**: `afrotc695-recruitment`
   - **Framework Preset**: Other
   - **Root Directory**: `./` (root of repository)
   - **Build Command**: Leave empty (handled by vercel.json)
   - **Output Directory**: Leave empty (handled by vercel.json)

### Step 2: Configure Environment Variables

In the Vercel dashboard, go to your project settings and add these environment variables:

#### Database Configuration
```
DATABASE_URL=postgresql://neondb_owner:PASSWORD@HOST.neon.tech/neondb?sslmode=require
```

#### Vercel Blob Storage
```
BLOB_READ_WRITE_TOKEN=vercel_blob_rw_REPLACE_WITH_YOUR_TOKEN
```

#### Flask Configuration
```
SECRET_KEY=your-super-secret-key-change-this-in-production
FLASK_ENV=production
```

#### Additional Configuration
```
BCRYPT_ROUNDS=12
LOG_LEVEL=info
MAX_FILE_SIZE=5242880
```

### Step 3: Deploy

1. **Initial Deployment**
   - Click "Deploy" in the Vercel dashboard
   - Vercel will automatically detect the Python Flask app
   - The deployment will use the `vercel.json` configuration

2. **Monitor Deployment**
   - Watch the build logs for any errors
   - Ensure all dependencies are installed correctly
   - Verify the Flask app starts successfully

### Step 4: Verify Deployment

1. **Check Application**
   - Visit your Vercel deployment URL
   - Test the login functionality
   - Verify database connectivity
   - Test file upload/download functionality

2. **Check Logs**
   - Go to Functions tab in Vercel dashboard
   - Check for any runtime errors
   - Monitor performance metrics

## 🔧 Configuration Details

### vercel.json Structure

```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/app.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/static/(.*)",
      "dest": "/static/$1"
    },
    {
      "src": "/(.*)",
      "dest": "/api/app.py"
    }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "Strict-Transport-Security",
          "value": "max-age=31536000; includeSubDomains; preload"
        },
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "X-Frame-Options",
          "value": "SAMEORIGIN"
        },
        {
          "key": "X-XSS-Protection",
          "value": "1; mode=block"
        },
        {
          "key": "Referrer-Policy",
          "value": "strict-origin-when-cross-origin"
        }
      ]
    }
  ],
  "env": {
    "FLASK_ENV": "production"
  }
}
```

### Database Configuration

The application uses Neon PostgreSQL with:
- **Connection pooling**: Configured for serverless compatibility
- **SSL**: Required for Neon connections
- **NullPool**: Used to prevent connection pooling issues

### File Storage

All file uploads and downloads use Vercel Blob storage:
- **Uploads**: Files stored with timestamps
- **Downloads**: Direct blob URL access
- **Backups**: Database backups stored in blob

## 🏠 Local Development

### Setup Local Environment

1. **Install Dependencies**
   ```bash
   pip install -r requirements_local.txt
   ```

2. **Configure Environment**
   - Copy `env.local` with your credentials
   - Ensure all environment variables are set

3. **Start Local Server**
   ```bash
   python start_local.py
   ```

### Local vs Production

- **Same Database**: Local uses the same Neon database as production
- **Same File Storage**: Local uses the same Vercel Blob storage
- **Same Code Paths**: Local `app_local.py` mirrors production `api/app.py`
- **Development Features**: Local includes debug mode and development tools

## 🔒 Security Considerations

### Production Security

1. **HTTPS**: Automatically enabled by Vercel
2. **Security Headers**: Configured in vercel.json
3. **Environment Variables**: Securely stored in Vercel dashboard
4. **Database**: SSL-encrypted connections to Neon

### Access Control

1. **User Authentication**: Required for all sensitive operations
2. **Role-Based Access**: Different permissions for different user roles
3. **Activity Logging**: All user actions are logged
4. **Session Management**: Secure session handling

## 🛠️ Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify DATABASE_URL is correct
   - Check Neon database is accessible
   - Ensure SSL is enabled

2. **Blob Storage Errors**
   - Verify BLOB_READ_WRITE_TOKEN is correct
   - Check Vercel Blob storage is accessible
   - Ensure proper permissions

3. **Import Errors**
   - Check all dependencies are in requirements.txt
   - Verify Python version compatibility
   - Check for missing packages

4. **Build Failures**
   - Check vercel.json configuration
   - Verify file paths are correct
   - Check for syntax errors in Python code

### Debugging

1. **Check Vercel Logs**
   - Go to Functions tab in dashboard
   - View real-time logs
   - Check for error messages

2. **Test Locally First**
   - Use local environment for testing
   - Verify functionality before deploying
   - Check environment variables

3. **Database Issues**
   - Test database connection locally
   - Verify schema is correct
   - Check for migration issues

## 📊 Monitoring and Maintenance

### Performance Monitoring

1. **Vercel Analytics**
   - Monitor page views and performance
   - Track function execution times
   - Monitor error rates

2. **Database Monitoring**
   - Monitor Neon database performance
   - Check connection pool usage
   - Monitor query performance

3. **Storage Monitoring**
   - Monitor Vercel Blob usage
   - Track file upload/download metrics
   - Monitor storage costs

### Backup and Recovery

1. **Database Backups**
   - Automated backups via Neon
   - Manual backups through application
   - Backup verification procedures

2. **File Storage Backups**
   - Vercel Blob redundancy
   - Manual backup procedures
   - Recovery testing

## 🔄 Updates and Maintenance

### Deployment Updates

1. **Code Updates**
   - Push changes to Git repository
   - Vercel automatically redeploys
   - Monitor deployment success

2. **Environment Variable Updates**
   - Update in Vercel dashboard
   - Redeploy to apply changes
   - Test functionality

3. **Dependency Updates**
   - Update requirements.txt
   - Test locally first
   - Deploy and monitor

### Maintenance Schedule

1. **Weekly**
   - Check application logs
   - Monitor performance metrics
   - Verify backup success

2. **Monthly**
   - Review security settings
   - Update dependencies
   - Performance optimization

3. **Quarterly**
   - Security audit
   - Database optimization
   - Storage cleanup

## 📞 Support

### Getting Help

1. **Vercel Documentation**: [vercel.com/docs](https://vercel.com/docs)
2. **Neon Documentation**: [neon.tech/docs](https://neon.tech/docs)
3. **Flask Documentation**: [flask.palletsprojects.com](https://flask.palletsprojects.com)

### Emergency Procedures

1. **Application Down**
   - Check Vercel status page
   - Verify environment variables
   - Check function logs

2. **Database Issues**
   - Check Neon status page
   - Verify connection strings
   - Test database connectivity

3. **File Storage Issues**
   - Check Vercel Blob status
   - Verify API tokens
   - Test blob operations

## 🎯 Success Metrics

### Deployment Success Criteria

- ✅ Application accessible via Vercel URL
- ✅ Database connectivity working
- ✅ File upload/download functional
- ✅ User authentication working
- ✅ All features operational
- ✅ Security headers configured
- ✅ SSL/HTTPS enabled
- ✅ Performance acceptable

### Performance Targets

- **Page Load Time**: < 2 seconds
- **Function Response Time**: < 1 second
- **Database Query Time**: < 500ms
- **File Upload Time**: < 5 seconds (for 5MB files)
- **Uptime**: > 99.9%

---

**Last Updated**: December 2024
**Version**: 1.0
**Project ID**: prj_Dp0OjBia3YoTgbCxwQdkKr6BSSIz
