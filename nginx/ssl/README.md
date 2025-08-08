# SSL Certificates

This directory should contain SSL certificates for production deployment.

## For Development

No SSL certificates are needed for local development.

## For Production

Add your SSL certificates:
- `cert.pem` - SSL certificate
- `key.pem` - Private key
- `chain.pem` - Certificate chain (if applicable)

## Generate Self-Signed Certificate for Testing

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout key.pem \
  -out cert.pem \
  -config <(
    echo '[dn]'
    echo 'CN=localhost'
    echo '[req]'
    echo 'distinguished_name = dn'
  )
```

## Important Security Notes

- Never commit actual SSL certificates to version control
- Use environment variables or secure secret management for certificate paths
- Ensure certificates are properly validated and from trusted CAs in production
- Consider using Let's Encrypt for free SSL certificates