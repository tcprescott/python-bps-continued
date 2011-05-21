# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

"""
Utility methods used when reading Blip patches.
"""
# For copyright and licensing information, see the file COPYING.
import io
from zlib import crc32
from blip import constants as C

class CRCIOWrapper(io.IOBase):
	"""
	A wrapper for an IO instance that tracks the CRC32 of data read or written.

	This wrapper prohibits seeking. It doesn't prohibit reading from and
	writing to the same file, but that's not a very smart thing to do.
	"""

	def __init__(self, inner):
		self.inner = inner
		self.crc32 = 0

	def _update_crc32(self, data):
		self.crc32 = crc32(data, self.crc32) & 0xffffffff
		return data

	def __getattr__(self, name):
		return getattr(self.inner, name)

	# Methods from IOBase

	def readline(self, *args, **kwargs):
		return self._update_crc32(self.inner.readline(*args,**kwargs))

	def readlines(self, *args, **kwargs):
		return [
				self._update_crc32(line)
				for line in self.inner.readlines(*args, **kwargs)
			]

	def seek(self, *args, **kwargs):
		raise io.UnsupportedOperation("Seeking not supported.")

	def truncate(self, size=None):
		if size not in (None, 0):
			raise io.UnsupportedOperation(
					"Cannot truncate to size {0}".format(size)
				)

		if size == 0:
			self.crc32 = 0

		return self.inner.truncate(size)

	def writelines(self, lines):
		return self.inner.writelines([
				self._update_crc32(line)
				for line in lines
			])

	# Methods from RawIOBase
	
	def read(self, *args, **kwargs):
		return self._update_crc32(self.inner.read(*args,**kwargs))

	def readall(self, *args, **kwargs):
		return self._update_crc32(self.inner.readall(*args,**kwargs))

	def readinto(self, *args, **kwargs):
		return self._update_crc32(self.inner.readinto(*args,**kwargs))

	def write(self, data):
		return self.inner.write(self._update_crc32(data))

	# Methods from BufferedIOBase
	
	def read1(self, *args, **kwargs):
		return self._update_crc32(self.inner.read1(*args,**kwargs))


def read_var_int(handle):
	"""
	Read a variable-length integer from the given file handle.
	"""
	res = 0
	shift = 1

	while True:
		byte = handle.read(1)[0]
		res += (byte & 0x7f) * shift
		if byte & 0x80: break
		shift <<= 7
		res += shift

	return res


def encode_var_int(number):
	"""
	Returns a bytearray encoding the given number.
	"""
	buf = bytearray()
	shift = 1

	while True:
		buf.append(number & 0x7F)

		number -= buf[-1]

		if number == 0:
			buf[-1] |= 0x80
			break

		number -= shift
		number >>= 7
		shift += 7

	return buf


def write_var_int(number, handle):
	"""
	Writes a variable-length integer to the given file handle.
	"""
	handle.write(encode_var_int(number))


def op_size(op):
	"""
	Returns the number of bytes written by the given operation.

	Returns None if the operation in question does not write bytes (such as
	SOURCECRC32 or TARGETCRC32).
	"""
	if op[0] in (C.SOURCEREAD, C.SOURCECOPY, C.TARGETCOPY):
		return op[1]
	elif op[0] == C.TARGETREAD:
		return len(op[1])
