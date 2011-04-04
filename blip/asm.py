# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

"""
Tools for creating human-readable versions of Blip patch files.
"""
import blip.io as bio

def disassemble(in_buf, out_buf):
	"""
	Disassembles the Blip patch in in_buf, writing the result to out_buf.

	in_buf should implement io.IOBase, opened in 'rb' mode.

	out_buf should implement io.IOBase, opened in 'wt' mode.
	"""
	bio.write_blip_asm(bio.read_blip(in_buf), out_buf)


def assemble(in_buf, out_buf):
	"""
	Assembles the description in in_buf to a Blip patch in out_buf.

	in_buf should implement io.IOBase, opened in 'rt' mode.

	out_buf should implement io.IOBase, opened in 'wb' mode.
	"""
	bio.write_blip(bio.read_blip_asm(in_buf), out_buf)
