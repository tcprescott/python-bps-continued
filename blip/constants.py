BLIP_MAGIC = b'blip'
BLIPASM_MAGIC = 'blipasm'

# Headings used by the blip assembly format.
SOURCESIZE  = "sourcesize"
TARGETSIZE  = "targetsize"
METADATA    = "metadata"
SOURCECRC32 = "sourcecrc32"
TARGETCRC32 = "targetcrc32"
PATCHCRC32  = "patchcrc32" # not actually used by the assembly language

# Values used in patch-hunk encoding.
SOURCEREAD = 0b00
TARGETREAD = 0b01
SOURCECOPY = 0b10
TARGETCOPY = 0b11

OPCODEMASK = 0b11
OPCODESHIFT = 2
