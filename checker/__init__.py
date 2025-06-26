import aiohttp
from cryptography import x509
from async_lru import alru_cache
from checker.ocsp_utils import _ocsp_check
from checker.entitlement_utils import check_entitlements
from checker.certificate_utils import extract_cert_from_mobileprovision, extract_cert_from_p12, get_certificate_info


@alru_cache(ttl=60 * 60) # Cache for 1 hour
async def fetch_certificate(session, url):
    async with session.get(url) as response:
        return await response.read()


async def check(mobileprovision_bytes: bytes = None, p12_bytes: bytes = None, password: str = ""):
    try:
        if mobileprovision_bytes:
            p12_cert, entitlements = extract_cert_from_mobileprovision(mobileprovision_bytes)
            cert_info = get_certificate_info(p12_cert)
            entitlements_info = check_entitlements(entitlements)
        elif p12_bytes:
            p12_cert = extract_cert_from_p12(p12_bytes, password)
            cert_info = get_certificate_info(p12_cert)
            entitlements_info = "Not applicable for p12 files"
        else:
            raise ValueError("Either mobileprovision_path or p12_path must be provided.")
    except Exception as e:
        raise e 

    ca_certs = ["AppleWWDRCA", "AppleWWDRCAG2", "AppleWWDRCAG3", "AppleWWDRCAG4", "AppleWWDRCAG5", "AppleWWDRCAG6"]
    ocsp_status = "Unknown"

    async with aiohttp.ClientSession() as session:
        for cert in ca_certs:
            try:
                url = (
                    "https://developer.apple.com/certificationauthority/AppleWWDRCA.cer"
                    if cert.endswith("A")
                    else f"https://www.apple.com/certificateauthority/{cert}.cer"
                )
                ca_cert_data = await fetch_certificate(session, url)
                ca_cert = x509.load_der_x509_certificate(ca_cert_data)
                ocsp_status = _ocsp_check(p12_cert, ca_cert, cert_info["ocsp_url"])

                if ocsp_status in ["ENABLED", "REVOKED"]:
                    break
            except Exception as e:
                ocsp_status = f"OCSP check failed: {str(e)}"

    result = {
        "certificate_info": cert_info,
        "certificate_status": ocsp_status,
        "entitlements": entitlements_info
    }

    return result
