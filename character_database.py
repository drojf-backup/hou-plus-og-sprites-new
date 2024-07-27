
import re


RENA = 'rena'
KEIICHI = 'keiichi'
SHION = 'shion'
RIKA = 'rika'
HANYU = 'hanyu'
SATOKO = 'satoko'
MION = 'mion'
IRIE = 'irie'
MOB_CHARACTER = 'mob'
KAMEDA = 'kameda'
OKONOGI = 'okonogi'
OISHI = 'oishi'
TAKANO = 'takano'
TETU = 'tetu'
MURA = 'mura'
UNE = 'une'
TAMURA = 'tamura'
KUMI_1 = 'kumi1'
KUMI_2 = 'kumi2'

# Only used in staffroom15?
SATOSHI = 'satoshi'
TOMITAKE = 'tomitake'
KASAI = 'kasai'
AKASAKA = 'akasaka'

# Silhouettes - should these be handled differently?
MION_SILHOUETTE = 'mion_silhouette'
RIKA_SILHOUETTE = 'rika_silhouette'
TON_SILHOUETTE = 'ton_silhouette'
ARA_SILHOUETTE = 'ara_silhouette'
YOS_SILHOUETTE = 'yos_silhouette'
OKA_SILHOUETTE = 'oka_silhouette'
HOS_SILHOUETTE = 'hos_silhouette'
ODA_SILHOUETTE = 'oda_silhouette'
HOT_SILHOUETTE = 'hot_silhouette'
NIT_SILHOUETTE = 'nit_silhouette'

KEI_SILHOUETTE = 'kei_silhouette'
OYASHIRO_SILHOUETTE = 'oyashiro_silhouette'

# Mob characters
MOB_1 = 'mob_character_1'
MOB_2 = 'mob_character_2'
MOB_3 = 'mob_character_3'

# for item in OG_TO_REGEX:
#     complete_regex = f'"({item}[^"]*)"'
#     print(complete_regex)
#     OG_SHOULD_PROCESS_REGEX.append(
#         re.compile(complete_regex)
#     )

mod_to_name = {
    're': RENA,
    # renasen is rena with hatchet, but just mapping to RENA should generally be OK
    'renasen': RENA,
    'si': SHION,
    'kei': KEIICHI,
    # keisen is rena with hatchet, but just mapping to RENA should generally be OK
    'keisen': KEIICHI,
    'ri': RIKA,
    'ha': HANYU,
    'sa': SATOKO,
    'me': MION,
    'iri': IRIE,
    'mo': MOB_CHARACTER,
    'kameda': KAMEDA,
    'oko': OKONOGI,
    'oisi': OISHI,
    'ta': TAKANO,
    'tetu': TETU,
    'mura': MURA,
    'une': UNE,
    'tamura': TAMURA,
    # Special case - mob characters with similar name
    'kumi1': KUMI_1,
    'kumi2': KUMI_2,

    # Only used in staffroom15?
    'sato': SATOSHI,
    'tomi': TOMITAKE,
    'kasa': KASAI,
    'kas': KASAI,
    'aks': AKASAKA,


    # Silhouettes - should these be handled differently?
    'hmi': MION_SILHOUETTE,
    'hri': RIKA_SILHOUETTE,
    'hton':TON_SILHOUETTE,
    'hara': ARA_SILHOUETTE,
    'hyos': YOS_SILHOUETTE,
    'hoka': OKA_SILHOUETTE,
    'hhos': HOS_SILHOUETTE,
    'hoda': ODA_SILHOUETTE,
    'hhot': HOT_SILHOUETTE,
    'hnit': NIT_SILHOUETTE,

    # Mob characters
    'mo1': MOB_1,
    'mo2': MOB_2,
    'mo3': MOB_3,
}

mod_effect_to_name = {
    'hara': ARA_SILHOUETTE,
    'hnit':  NIT_SILHOUETTE,
    'hoda': ODA_SILHOUETTE,
    'hoka': OKA_SILHOUETTE,
    'hton':  TON_SILHOUETTE,
    'hyos': YOS_SILHOUETTE,
    'kei': KEI_SILHOUETTE,
    'oyasiro': OYASHIRO_SILHOUETTE,
}

# TODO: check other chars (eg mo2, mo3, mo4) if they appear in og script
# or rather, scan OG script for all used sprites, not just mod script

name_to_og = {
    RENA: 'rena',
    SHION: 'sion',
    KEIICHI: 'keiiti',
    RIKA: 'rika',
    HANYU: 'hanyu',
    SATOKO: 'satoko',
    MION: 'mion',
    IRIE: 'irie',
    MOB_CHARACTER: 'mob',
    KAMEDA: 'kam',
    OKONOGI: 'okonogi',
    OISHI: 'oisi',
    TAKANO: 'takano',
    TETU: 'tetu',
    MURA: 'mo1', # NOTE: In OG, mob character 1 is used instead of MURA's sprite (?). So both MURA and MOB_1 map to 'mo1'
    UNE: 'une',
    TAMURA: 'tam',
    # Special case - mob characters with similar name
    KUMI_1: 'mo6',
    KUMI_2: 'mo5',

    # Only used in staffroom15?
    SATOSHI: 'sato',
    TOMITAKE: 'tomi',
    KASAI: 'kasai',
    AKASAKA: 'aks',

    # Silhouettes - should these be handled differently?
    MION_SILHOUETTE: 'mio',
    RIKA_SILHOUETTE: 'rik',
    TON_SILHOUETTE: 'ton',
    ARA_SILHOUETTE: 'ara',
    YOS_SILHOUETTE: 'yos',
    OKA_SILHOUETTE: 'oka',
    HOS_SILHOUETTE: 'hos',
    ODA_SILHOUETTE: 'oda',
    HOT_SILHOUETTE: 'hod',
    NIT_SILHOUETTE: 'nit',

    # Mob characters
    MOB_1: 'mo1', # NOTE: In OG, mob character 1 is used instead of MURA's sprite (?). So both MURA and MOB_1 map to 'mo1'
    MOB_2: 'mo2',
    MOB_3: 'mo3',
}