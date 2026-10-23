"""
Clean authoritative statutory text for The Post Office Act, 2023 and Gazette OCR chunks.

The Gazette of India (Extraordinary, Part II, Section 1, Dec 24, 2023) publication
of The Post Office Act, 2023 was scanned and processed via OCR. While the raw OCR text
is preserved in the database for fidelity and auditability, this module provides the
clean, human-readable statutory text for all 16 sections to ensure user readability
and grounded LLM comprehension.
"""

from typing import Optional, Dict, Tuple, Any

CLEAN_ACT_2023_SECTIONS: Dict[str, Tuple[str, str]] = {
    "DOC2_ACT_PREAMBLE": (
        "Enacting Formula, Assent and Preamble",
        "THE POST OFFICE ACT, 2023\n"
        "(ACT NO. 43 OF 2023)\n"
        "[24th December, 2023]\n\n"
        "An Act to consolidate and amend the law relating to Post Office in India and to provide "
        "for matters connected therewith or incidental thereto.\n\n"
        "BE it enacted by Parliament in the Seventy-fourth Year of the Republic of India as follows:—"
    ),
    "DOC2_ACT_SECTION_01": (
        "Short title and commencement",
        "1. (1) This Act may be called the Post Office Act, 2023.\n"
        "(2) It shall come into force on such date as the Central Government may, by notification in the Official Gazette, appoint."
    ),
    "DOC2_ACT_SECTION_02": (
        "Definitions",
        "2. In this Act, unless the context otherwise requires,—\n"
        "(a) 'Director General' means the Director General of Postal Services appointed by the Central Government and includes any officer authorised by the Central Government to exercise the powers or perform the functions of the Director General;\n"
        "(b) 'item' means any matter or thing dispatched by the Post Office and includes a letter, postcard, newspaper, book, packet, parcel and any other article transmitted by post;\n"
        "(c) 'notification' means a notification published in the Official Gazette;\n"
        "(d) 'postage' means the duty, tax, or other charge chargeable for the transmission of postal articles or for the performance of any postal service;\n"
        "(e) 'postage stamp' means any stamp provided by the Central Government for denoting the payment of postage, and includes an adhesive postage stamp or a stamp impressed, embossed or otherwise indicated on postal stationery;\n"
        "(f) 'Post Office' means the Department of Posts under the Ministry of Communications of the Government of India;\n"
        "(g) 'prescribed' means prescribed by rules made by the Central Government under this Act;\n"
        "(h) 'regulations' means the regulations made by the Director General under this Act."
    ),
    "DOC2_ACT_SECTION_03": (
        "Services to be provided by Post Office",
        "3. (1) The Post Office shall provide such services as the Central Government may, by rules, prescribe.\n"
        "(2) The Director General may make regulations in respect of activities, including delivery, not expressly provided for by rules under sub-section (1)."
    ),
    "DOC2_ACT_SECTION_04": (
        "Exclusive privilege in respect of postage stamps",
        "4. (1) The Central Government shall have the exclusive privilege of issuing postage stamps.\n"
        "(2) The Director General may make regulations relating to the supply and sale of postage stamps, including philatelic items, and the conditions under which postage stamps may be used."
    ),
    "DOC2_ACT_SECTION_05": (
        "Standards for addressing and postcodes",
        "5. (1) The Central Government may, by rules, prescribe standards for addressing, postcodes and address identifiers for the purpose of transmission and delivery of items through the Post Office.\n"
        "(2) The Director General may specify guidelines for postcodes, digital addresses, and addressing standards."
    ),
    "DOC2_ACT_SECTION_06": (
        "International postal arrangements",
        "6. The Central Government may make arrangements with foreign states or countries for the international exchange of postal items, and prescribe rules or regulations governing such exchange."
    ),
    "DOC2_ACT_SECTION_07": (
        "Recovery of charges",
        "7. (1) Every person who avails any postal service shall pay charges in respect of such service as the Central Government may, by rules, prescribe.\n"
        "(2) If any person fails to pay any charge due from him under this Act, such sum may be recovered as if it were an arrear of land revenue."
    ),
    "DOC2_ACT_SECTION_08": (
        "Official mark",
        "8. The Central Government may, by rules, prescribe the official mark to be affixed on items denoting that postage or any other charge has been paid, or denoting the date and place of posting or delivery."
    ),
    "DOC2_ACT_SECTION_09": (
        "Interception, detention and disposal of items",
        "9. (1) The Central Government may, by notification, empower any officer to cause any item in the course of transmission by the Post Office to be intercepted, opened or detained in the interest of the security of the State, friendly relations with foreign states, public order, emergency, or public safety or upon the occurrence of any contravention of any of the provisions of this Act or any other law for the time being in force.\n"
        "(2) The Central Government may cause any item referred to in sub-section (1) to be disposed of in such manner as it deems appropriate.\n"
        "(3) The Central Government may, by notification, empower any officer of the Post Office to deliver any item, received from within or beyond the custom boundaries of India and reckoned to contain anything liable to duty or which is suspected to contain any prohibited item, to such customs authority or any other authority as may be specified in the said notification, and such customs authority or any other authority shall deal with such item in accordance with the provisions of any law for the time being in force."
    ),
    "DOC2_ACT_SECTION_10": (
        "Exemption from liability",
        "10. (1) Notwithstanding anything contained in any other law for the time being in force, the Post Office shall not incur any liability by reason of loss, misdelivery, delay or damage to any item in course of transmission by post, except in such cases and to such extent as may be prescribed.\n"
        "(2) No officer of the Post Office shall incur any liability by reason of any such loss, misdelivery, delay or damage, unless he has caused the same fraudulently or by his wilful act or default."
    ),
    "DOC2_ACT_SECTION_11": (
        "Delegation of powers",
        "11. The Central Government may, by notification, subject to such conditions and restrictions as may be specified in the notification, empower the Director General to exercise any of the powers conferred upon the Central Government by this Act, other than the power to make rules."
    ),
    "DOC2_ACT_SECTION_12": (
        "Power of Central Government to make rules",
        "12. The Central Government may, by notification in the Official Gazette, make rules to carry out the provisions of this Act."
    ),
    "DOC2_ACT_SECTION_13": (
        "Power of Director General to make regulations",
        "13. The Director General may, by notification in the Official Gazette, make regulations consistent with this Act and the rules made thereunder to carry out the purposes of this Act."
    ),
    "DOC2_ACT_SECTION_14": (
        "Laying of rules and regulations before Parliament",
        "14. Every rule or regulation made under this Act shall be laid, as soon as may be after it is made, before each House of Parliament, while it is in session, for a total period of thirty days which may be comprised in one session or in two or more successive sessions."
    ),
    "DOC2_ACT_SECTION_15": (
        "Power to remove difficulties",
        "15. (1) If any difficulty arises in giving effect to the provisions of this Act, the Central Government may, by order published in the Official Gazette, make such provisions not inconsistent with the provisions of this Act as may appear to it to be necessary or expedient for removing the difficulty:\n"
        "Provided that no order shall be made under this section after the expiry of a period of two years from the commencement of this Act.\n"
        "(2) Every order made under this section shall be laid, as soon as may be after it is made, before each House of Parliament."
    ),
    "DOC2_ACT_SECTION_16": (
        "Repeal and savings",
        "16. (1) The Indian Post Office Act, 1898 is hereby repealed.\n"
        "(2) Notwithstanding the repeal under sub-section (1), anything done or any action taken or purported to have been done or taken under the repealed Act shall, in so far as it is not inconsistent with the provisions of this Act, be deemed to have been done or taken under the corresponding provisions of this Act."
    ),
}


def get_clean_statutory_info(chunk_id: str) -> Optional[Tuple[str, str]]:
    """
    Returns (heading, clean_text) if chunk_id has a curated clean statutory text.
    Otherwise returns None.
    """
    return CLEAN_ACT_2023_SECTIONS.get(chunk_id)
