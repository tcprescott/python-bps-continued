BLIP_MAGIC = b'blip'
BLIPASM_MAGIC = 'blipasm\n'

# Headings used by the blip assembly format.
SOURCESIZE  = "sourcesize"
TARGETSIZE  = "targetsize"
METADATA    = "metadata"
SOURCEREAD  = "sourceread"
TARGETREAD  = "targetread"
SOURCECOPY  = "sourcecopy"
TARGETCOPY  = "targetcopy"
SOURCECRC32 = "sourcecrc32"
TARGETCRC32 = "targetcrc32"

# Values used in patch-hunk encoding.
OP_SOURCEREAD = 0b00
OP_TARGETREAD = 0b01
OP_SOURCECOPY = 0b10
OP_TARGETCOPY = 0b11

OPCODEMASK = 0b11
OPCODESHIFT = 2
