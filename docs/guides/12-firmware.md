# 12. Firmware

> Every example needs a live server, and several also need Cisco.com credentials and
> internet access. Signatures verified by introspection.

```python
from ucscsdk.utils.ucscfirmware import get_firmware_bundles

for b in get_firmware_bundles(handle, bundle_type="b-series-bundle"):
    print(b.name, b.version)
```

## Listing bundles

```python
get_firmware_bundles(handle, bundle_type=None, fw_platform=None)
```

```python
get_firmware_bundles(handle)                                    # everything
get_firmware_bundles(handle, bundle_type="b-series-bundle")
get_firmware_bundles(handle, bundle_type="infrastructure-bundle",
                     fw_platform="mini")
```

Returns bundles already imported into UCS Central plus those available for import.

Bundles that failed to download:

```python
from ucscsdk.utils.ucscfirmware import get_failed_dw_firmware_bundles
get_failed_dw_firmware_bundles(handle)
```

Worth checking before concluding an image is simply missing.

## Importing an image

**From your machine:**

```python
from ucscsdk.utils.ucscfirmware import firmware_add_local

firmware_add_local(handle, "/home/user/Downloads/",
                   "ucs-k9-bundle-b-series.3.1.1h.B.bin")
```

```python
firmware_add_local(handle, local_path, file_name, timeout=900, progress=Progress())
```

The upload can be large; `timeout` defaults to 900 seconds. A `progress` object prints
progress — pass your own to silence or redirect it.

**From a remote host:**

```python
from ucscsdk.utils.ucscfirmware import firmware_add_remote

firmware_add_remote(handle, remote_path="/images/",
                    file_name="ucs-k9-bundle-b-series.3.1.1h.B.bin",
                    protocol="scp", hostname="10.10.1.1",
                    username="guest", password="password")
```

UCS Central fetches it directly — no data flows through your machine, which is much faster
for large bundles.

**Removing:**

```python
from ucscsdk.utils.ucscfirmware import firmware_remove
firmware_remove(handle, image_name="ucs-k9-bundle-b-series.3.1.1h.B.bin")
```

## Downloading from Cisco.com

```python
from ucscsdk.utils.ucscfirmware import get_cco_firmware_image

get_cco_firmware_image(image_name="ucs-central-bundle.1.5.1a.bin",
                       username="cisco_user", password="cisco_password",
                       download_dir="/home/user/Downloads/")
```

```python
get_cco_firmware_image(image_name, username, password, download_dir,
                       mdf_id_list=(284308174,), proxy=None, progress=Progress())
```

These are your **Cisco.com** credentials, not UCS credentials, and the download requires a
valid service contract. `mdf_id_list` selects the product families to search; the default
covers UCS Central. Add IDs to reach UCS infrastructure or B/C-series bundles.

The image lands in `download_dir` on your machine — import it afterwards with
`firmware_add_local`.

To browse rather than fetch:

```python
from ucscsdk.utils.ccoimage import get_ucsc_cco_image_list, get_ucsc_cco_image

images = get_ucsc_cco_image_list(username="cisco_user", password="cisco_password")
get_ucsc_cco_image(images[0], file_dir="/home/user/Downloads/")
```

## Scheduling an infrastructure update

```python
from ucscsdk.utils.ucscfirmware import schedule_infra_fw_update

schedule_infra_fw_update(handle, domain_group="root", schedule="now")

schedule_infra_fw_update(handle, domain_group="root",
                         schedule="2026-08-31T22:33:07",
                         fi_mini_6300_ver="3.1(1j)A",
                         catalog_ver="3.1(1)T")
```

```python
schedule_infra_fw_update(handle, domain_group, schedule, user_ack_en=True,
                         fi_6100_6200_ver=None, fi_mini_6300_ver=None,
                         fi_6300_ver=None, catalog_ver=None)
```

`schedule` is `"now"` or an ISO-8601 timestamp. The version arguments target specific
hardware generations — set only the ones that apply to the domain group.

`user_ack_en=True` (the default) means the update waits for administrator acknowledgement
before rebooting fabric interconnects. **Leaving it on is the safe choice**; setting it
`False` lets a reboot happen unattended.

## Syncing the catalogue from Cisco

```python
from ucscsdk.utils.ucscfirmware import sync_firmware_update_from_cisco

sync_firmware_update_from_cisco(handle,
                                cisco_username="cisco_user",
                                cisco_password="cisco_password",
                                sync_enable=True,
                                sync_frequencey="weekly",
                                proxy_enable=False)
```

```python
sync_firmware_update_from_cisco(handle, cisco_username, cisco_password,
                                sync_enable=False, sync_frequencey='daily',
                                proxy_enable=False, proxy_name_or_ip=None,
                                proxy_port=None, proxy_username='',
                                proxy_password='')
```

**`sync_frequencey` is misspelled in the SDK.** That is the real parameter name — spelling
it correctly raises `TypeError`. Accepted values include `"daily"` and `"weekly"`.

Behind a proxy:

```python
sync_firmware_update_from_cisco(handle,
                                cisco_username="cisco_user",
                                cisco_password="cisco_password",
                                sync_enable=True,
                                proxy_enable=True,
                                proxy_name_or_ip="192.168.1.10",
                                proxy_port="8080",
                                proxy_username="proxyuser",
                                proxy_password="proxypassword")
```

## Checking versions

```python
handle.get_firmware_version()      # e.g. '2.0(1a)'
```

Raises `UcscOperationError` if the version object cannot be resolved.

Do **not** use `handle.is_local_download_supported()`. It imports `distutils`, which was
removed in Python 3.13, so it raises `ModuleNotFoundError` there. Its logic is also
inverted relative to its name — it returns `False` for version 1.5 and above. Compare
versions yourself:

```python
from ucscsdk.ucsccoremeta import UcscVersion
UcscVersion(handle.get_firmware_version()) >= UcscVersion("1.5(1a)")
```

## Credentials

Cisco.com credentials appear in several of these calls. Read them from the environment:

```python
import os
get_cco_firmware_image(image_name="ucs-central-bundle.1.5.1a.bin",
                       username=os.environ["CCO_USER"],
                       password=os.environ["CCO_PASS"],
                       download_dir="/home/user/Downloads/")
```

## Common errors

**`TypeError: sync_firmware_update_from_cisco() got an unexpected keyword argument
'sync_frequency'`** — the parameter is `sync_frequencey`. The typo is in the SDK.

**Timeout during `firmware_add_local`** — raise `timeout` above 900, or use
`firmware_add_remote` so UCS Central fetches the file itself.

**`get_cco_firmware_image` fails to authenticate** — Cisco.com credentials, and the account
needs a service contract covering that image.

**Image not found on Cisco.com** — the default `mdf_id_list` only covers UCS Central. Pass
the IDs for the product family you want.

**`ModuleNotFoundError: No module named 'distutils'`** — you called
`is_local_download_supported()` on Python 3.13+. Compare versions with `UcscVersion` instead.

**`UcscOperationError` from `get_firmware_version`** — the version object did not resolve
uniquely; usually a connectivity or privilege problem.

**Scheduled update did not run** — `user_ack_en=True` means it is waiting for
acknowledgement. That is the intended safety behaviour.

**Bundle appears absent after import** — check `get_failed_dw_firmware_bundles(handle)`; the
download may have failed rather than the import.
