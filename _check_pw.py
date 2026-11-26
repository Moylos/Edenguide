import hashlib
salt='8e789b37bca2ef8d47ab992441306a22'
h=hashlib.pbkdf2_hmac('sha256',b'admin123',bytes.fromhex(salt),100000).hex()
print(h == 'df71afdbc73c2f7076d857ee9360132b4991d9d05346d15ddfe9fc2611499338')
