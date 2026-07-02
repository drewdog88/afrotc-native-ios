# AFROTC 695 Neon Backup Scheduler (Serverless)

This system provides automatic nightly backups for the AFROTC 695 Recruitment System using PostgreSQL (Neon) and Vercel Blob storage, designed specifically for Vercel's serverless environment.

## Features

- **Nightly Backups**: Automatic backups at 2:00 AM every day via Vercel Cron Jobs
- **30-Day Retention**: Automatically removes backups older than 30 days
- **Cloud Storage**: All backups stored securely in Vercel Blob storage
- **JSON Format**: Backups in JSON format for easy restoration
- **Serverless Compatible**: Designed for Vercel's serverless environment
- **Metadata Tracking**: Each backup includes detailed metadata

## How It Works

### Vercel Cron Jobs (Production)
The system uses Vercel's built-in cron job functionality:

- **Nightly Backup**: Runs at 2:00 AM daily via `/api/backup/nightly`
- **Cleanup**: Runs at 3:00 AM daily via `/api/backup/cleanup`
- **Automatic**: No manual intervention required
- **Serverless**: Runs as serverless functions with time limits

### Local Development
For local development and testing, you can use the standalone scheduler:

```bash
# Run a single backup immediately
python neon_backup_scheduler.py --now

# Test the backup system
python neon_backup_scheduler.py --test
```

## Configuration

### Vercel Configuration (`vercel.json`)
```json
{
  "functions": {
    "api/app.py": {
      "maxDuration": 60
    }
  },
  "crons": [
    {
      "path": "/api/backup/nightly",
      "schedule": "0 2 * * *"
    },
    {
      "path": "/api/backup/cleanup", 
      "schedule": "0 3 * * *"
    }
  ]
}
```

### Environment Variables
Required environment variables:

- `DATABASE_URL`: Neon PostgreSQL connection string
- `BLOB_READ_WRITE_TOKEN`: Vercel Blob storage token

## Backup Schedule

- **Primary**: 2:00 AM daily (nightly backup)
- **Cleanup**: 3:00 AM daily (removes backups older than 30 days)
- **Retention**: 30 days (automatic cleanup)

## Backup Storage

- **Location**: Vercel Blob Storage
- **Format**: `afrotc695_backup_YYYYMMDD_HHMMSS.json`
- **Content**: Complete database export in JSON format
- **Tables**: All system tables including users, recruits, cadets, events, etc.

## Automatic Cleanup

The system automatically removes backups older than 30 days to:
- Prevent storage costs from accumulating
- Keep backup management simple
- Ensure only recent backups are available

## Monitoring

### Vercel Dashboard
- Monitor cron job execution in Vercel dashboard
- View function logs for backup operations
- Check function execution times and errors

### Manual Testing
Test the cron endpoints manually:

```bash
# Test backup endpoint
curl https://your-app.vercel.app/api/backup/nightly

# Test cleanup endpoint  
curl https://your-app.vercel.app/api/backup/cleanup
```

## Requirements

- **Production**: Vercel deployment with cron jobs enabled
- **Local**: Python 3.7+ with required packages
- **Packages**: `vercel-blob==0.4.2`, `sqlalchemy`, `schedule==1.2.0`
- **Environment**: `DATABASE_URL` and `BLOB_READ_WRITE_TOKEN` set

## Backup Format

Each backup file contains:

```json
{
  "timestamp": "20250807_233148",
  "description": "Nightly automatic backup",
  "created_at": "2025-08-07T23:31:48.123456",
  "tables": {
    "user": [...],
    "potential_recruit": [...],
    "cadet": [...],
    "university_contact": [...],
    "recruitment_event": [...],
    "external_link": [...],
    "recruitment_document": [...],
    "activity_log": [...],
    "password_history": [...]
  }
}
```

## Integration with Web Interface

The backup system integrates with the web interface:

- **Manual Backups**: Available through Admin → Database Management
- **Backup Listing**: Shows all available backups in the web interface
- **Backup Restoration**: Can restore from any backup through the web interface
- **Backup Deletion**: Can delete old backups through the web interface

## Troubleshooting

### Common Issues

1. **Cron Jobs Not Running**: Check Vercel dashboard for cron job status
2. **Function Timeout**: Increase `maxDuration` in `vercel.json` if needed
3. **Database Connection**: Verify `DATABASE_URL` is set correctly
4. **Blob Storage**: Verify `BLOB_READ_WRITE_TOKEN` is set correctly

### Error Messages

- **"Unauthorized"**: Expected for non-Vercel requests (security feature)
- **"Backup failed"**: Check database connection and blob storage
- **"Function timeout"**: Backup took too long, check database size

## Security

- Backups are stored securely in Vercel Blob storage
- Cron endpoints verify Vercel User-Agent for security
- Database credentials are handled securely
- Backup files are automatically cleaned up after 30 days

## Migration from Old System

This new system replaces the old MySQL-based backup scheduler:

- **Old**: `scheduled_backup.py` (MySQL + local files + continuous process)
- **New**: Vercel Cron Jobs (PostgreSQL + Vercel Blob + serverless)

The old system can be safely removed once the new system is confirmed working.

## Testing

### Local Testing
```bash
# Test cron endpoints
python test_cron_endpoints.py

# Test backup system
python neon_backup_scheduler.py --test

# Run manual backup
python neon_backup_scheduler.py --now
```

### Production Verification
- Check Vercel dashboard for cron job execution
- Verify backups appear in Vercel Blob storage
- Test manual backup through web interface
- Monitor cleanup operations
