# JADX keyword categories

This folder contains 19 personal-information categories for JADX output keyword scanning.

## Folder structure

```text
JADX_keyword_categories/
  README.md                         # This guide
  01_*.tsv ... 19_*.tsv             # Structured keyword dictionaries with confidence/type/notes
  grep_patterns/
    01_*.txt ... 19_*.txt           # Plain keyword files for rg/grep -f
```

## Category index

| No. | Category | TSV file | Grep pattern file |
| --- | --- | --- | --- |
| 01 | 基本身份、账号与实名认证信息 | `01_basic_identity_account_auth.tsv` | `grep_patterns/01_basic_identity_account_auth.txt` |
| 02 | 联系方式信息 | `02_contact_info.tsv` | `grep_patterns/02_contact_info.txt` |
| 03 | 设备信息与设备标识信息 | `03_device_identifiers.tsv` | `grep_patterns/03_device_identifiers.txt` |
| 04 | 网络身份标识与访问日志信息 | `04_network_identity_access_log.tsv` | `grep_patterns/04_network_identity_access_log.txt` |
| 05 | 位置信息 | `05_location.tsv` | `grep_patterns/05_location.txt` |
| 06 | 行踪轨迹信息 | `06_trajectory.tsv` | `grep_patterns/06_trajectory.txt` |
| 07 | 图像、音频、视频信息 | `07_image_audio_video.tsv` | `grep_patterns/07_image_audio_video.txt` |
| 08 | 生物识别信息 | `08_biometrics.tsv` | `grep_patterns/08_biometrics.txt` |
| 09 | 医疗健康信息 | `09_health_medical.tsv` | `grep_patterns/09_health_medical.txt` |
| 10 | 金融账户、财产与信用信息 | `10_financial_property_credit.tsv` | `grep_patterns/10_financial_property_credit.txt` |
| 11 | 交易与消费信息 | `11_transaction_consumption.tsv` | `grep_patterns/11_transaction_consumption.txt` |
| 12 | 行为记录与兴趣偏好信息 | `12_behavior_interest_preference.tsv` | `grep_patterns/12_behavior_interest_preference.txt` |
| 13 | 用户画像、算法标签与自动化决策相关信息 | `13_profile_algorithm_decision.tsv` | `grep_patterns/13_profile_algorithm_decision.txt` |
| 14 | 教育、职业与人力资源信息 | `14_education_career_hr.tsv` | `grep_patterns/14_education_career_hr.txt` |
| 15 | 社会关系信息 | `15_social_relationship.tsv` | `grep_patterns/15_social_relationship.txt` |
| 16 | 通信内容与互动信息 | `16_communication_content_interaction.tsv` | `grep_patterns/16_communication_content_interaction.txt` |
| 17 | 敏感身份与特殊身份信息 | `17_sensitive_special_identity.tsv` | `grep_patterns/17_sensitive_special_identity.txt` |
| 18 | 未成年人个人信息 | `18_minors.tsv` | `grep_patterns/18_minors.txt` |
| 19 | 个人公开信息 | `19_public_personal_info.tsv` | `grep_patterns/19_public_personal_info.txt` |

## File format

Each category TSV uses four columns:

```text
confidence<TAB>kind<TAB>pattern<TAB>note
```

- `H`: high confidence. Usually Android native API, Android constant, or explicit framework API.
- `M`: medium confidence. Usually SDK/API clue, permission, or clear business field name.
- `L`: low confidence. Business or Chinese keyword that often needs manual review.
- `kind`: `native_api`, `sdk_api`, `permission`, `business_keyword`, or `chinese_keyword`.
- `pattern`: literal string intended for grep/ripgrep over JADX output.

The `grep_patterns/` subfolder contains one plain pattern file per category. These files contain only the third column and can be used directly with ripgrep.
For native APIs, grep pattern files also include simple method-name aliases such as `getImei`, because JADX output often contains only the invoked method name instead of a full `Class.method` string.

## Scale policy

The default `grep_patterns/*.txt` files are balanced first-pass dictionaries. They keep explicit Android APIs, SDK names, permissions, and clear business fields, while suppressing very noisy compatibility/version fields and one-word generic terms such as `address`, `location`, `search`, or `comment`.

If you need maximum recall, inspect the matching `.tsv` file and manually add suppressed broad terms for a second pass. If a category is still noisy, first exclude common libraries in ripgrep, for example `-g '!androidx/**' -g '!kotlinx/**' -g '!org/webrtc/**'`.

## Suggested usage

```bash
jadx -d jadx_out app.apk
rg -n -F -i -f JADX_keyword_categories/grep_patterns/03_device_identifiers.txt jadx_out
```

If a hit is an `H` native API, it is a strong clue that the app collects or accesses that category. If a hit is `M` or `L`, inspect the surrounding code to decide whether it is real collection, UI text, dead code, an SDK constant, or an unrelated name.

## Important limitation

JADX keyword scanning is not taint analysis. It finds code evidence and suspicious terms. For business categories such as finance, education, special identity, minors, and public profile information, keyword hits must be manually checked against data flow and runtime context.
