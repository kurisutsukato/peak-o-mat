from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=1024,
    backend=default_backend()
)
public_key = private_key.public_key()


from cryptography.hazmat.primitives import serialization

pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

with open('private_key.pem', 'wb') as f:
    f.write(pem)


from cryptography.hazmat.primitives import serialization

pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

with open('public_key.pem', 'wb') as f:
    f.write(pem)

# read

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

with open("private_key.pem", "rb") as key_file:
    private_key = serialization.load_pem_private_key(
        key_file.read(),
        password=None,
        backend=default_backend()
    )

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

with open("public_key.pem", "rb") as key_file:
    public_key = serialization.load_pem_public_key(
        key_file.read(),
        backend=default_backend()
    )


from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

import hashlib, base64
from pickle import dumps, loads

def gen_license(msg):
    message = dumps(msg)

    prehashed = hashlib.sha256(message).digest()

    sig = private_key.sign(
        prehashed,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256())

    import textwrap

    lic = '{:04d}'.format(len(message)).encode('utf-8')+message+sig
    license = base64.b64encode(lic)
    out = '\n'.join(textwrap.wrap(license.decode('ascii'),32))
    return out

def read_license(license):
    license = license.replace('\n','').encode('ascii')

    try:
        lic = base64.b64decode(license)
    except:
        return False, None

    l = int(lic[:4])
    msg = lic[4:4+l]
    sig = lic[4+l:]

    try:
        message = loads(msg)
    except:
        return False, None

    prehashed = hashlib.sha256(msg).digest()

    try:
        public_key.verify(
            sig,
            prehashed,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256())
    except InvalidSignature:
        return False, message
    else:
        return True, message


if __name__ == '__main__':
    msg = {'name': 'Christian Kristukat',
           'email': 'ckkart@hoc.net',
           'affiliation': 'TU Berlin',
           'version': 1.2,
           'expiration': '190830'}

    lic = gen_license(msg)
    #print(lic)
    valid,lic = read_license(lic)
    print(valid)
    print(lic)
