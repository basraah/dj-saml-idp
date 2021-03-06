# -*- coding: utf-8 -*-
"""
Signing code goes here.
"""
from __future__ import absolute_import
import hashlib
import logging
import M2Crypto

from . import saml2idp_metadata as smd
from .codex import nice64
from . import xml_templates

logger = logging.getLogger(__name__)


def load_certificate(config):
    if smd.CERTIFICATE_DATA in config:
        return config.get(smd.CERTIFICATE_DATA, '')

    certificate_filename = config.get(smd.CERTIFICATE_FILENAME)
    logger.info('Using certificate file: {}'.format(certificate_filename))

    certificate = M2Crypto.X509.load_cert(certificate_filename)
    return ''.join(certificate.as_pem().decode("utf-8").split('\n')[1:-2])


def load_private_key(config):
    private_key_data = config.get(smd.PRIVATE_KEY_DATA)

    if private_key_data:
        return M2Crypto.EVP.load_key_string(private_key_data)

    private_key_file = config.get(smd.PRIVATE_KEY_FILENAME)
    logger.info('Using private key file: {}'.format(private_key_file))

    # The filename need to be encoded because it is using a C extension under
    # the hood which means it expects a 'const char*' type and will fail with
    # unencoded unicode string.
    if type(private_key_file) is bytes:
        private_key_file = private_key_file.decode('utf-8')
    return M2Crypto.EVP.load_key(private_key_file)


def sign_with_rsa(private_key, data):
    private_key.sign_init()
    private_key.sign_update(data.encode('utf-8'))
    return nice64(private_key.sign_final())


def get_signature_xml(subject: str, reference_uri: str) -> xml_templates.XmlTemplate.xml:
    """
    Returns XML Signature for subject.
    """
    # TODO: Replace with signxml
    logger.debug('get_signature_xml - Begin.')
    config = smd.SAML2IDP_CONFIG

    private_key = load_private_key(config)
    certificate = load_certificate(config)

    logger.debug('Subject: ' + subject)

    # Hash the subject.
    subject_hash = hashlib.sha1()
    subject_hash.update(subject.encode('utf-8'))
    subject_digest = nice64(subject_hash.digest()).decode('utf-8')
    logger.debug('Subject digest: {}'.format(subject_digest))

    # Create signed_info.
    signed_info = xml_templates.SignedInfoTemplate({
        'REFERENCE_URI': reference_uri,
        'SUBJECT_DIGEST': subject_digest,
        })
    logger.debug('SignedInfo XML: ' + signed_info.get_xml_string())

    rsa_signature = sign_with_rsa(private_key, signed_info.get_xml_string()).decode('utf-8')
    logger.debug('RSA Signature: {}'.format(rsa_signature))

    # Put the signed_info and rsa_signature into the XML signature.

    signature_xml = xml_templates.SignatureTemplate({
        'RSA_SIGNATURE': rsa_signature,
        'SIGNED_INFO': signed_info.xml,
        'CERTIFICATE': certificate,
        })

    logger.info('Signature XML: ' + signature_xml.get_xml_string())
    return signature_xml.xml
