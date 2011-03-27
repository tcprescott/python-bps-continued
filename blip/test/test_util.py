#!/usr/bin/python3
import unittest
import io
from blip import util
from zlib import crc32

EXAMPLE_VAR_INTS = {
		# Simple one-byte encodings
		b"\x80": 0,
		b"\x81": 1,
		b"\xFF": 127,
		# When we jump to two bytes, we 
		b"\x00\x80": 128,
		b"\x01\x80": 129,
		b"\x7F\x80": 255,
		b"\x00\x81": 256,
	}

class TestReadVarInt(unittest.TestCase):

	def testDecoding(self):
		"""
		Output matches our examples.
		"""
		for encoded, decoded in EXAMPLE_VAR_INTS.items():
			buf = io.BytesIO(encoded)
			self.assertEqual(util.read_var_int(buf), decoded)

	def testReadStopsAfterHighBitSet(self):
		"""
		Reader doesn't read past the byte wwith the high bit set.
		"""
		buf = io.BytesIO(b"\x00\x80\x10")
		self.assertEqual(util.read_var_int(buf), 128)
		self.assertEqual(buf.read(), b"\x10")

	def testReadComplainsAboutTruncatedData(self):
		"""
		Reader raises an exception if it can't find the end of a varint.
		"""
		buf = io.BytesIO(b"\x00\x00")
		self.assertRaises(Exception, util.read_var_int, buf)


class TestWriteVarInt(unittest.TestCase):

	def testEncoding(self):
		"""
		Output matches our examples.
		"""
		for encoded, decoded in EXAMPLE_VAR_INTS.items():
			buf = io.BytesIO()
			util.write_var_int(decoded, buf)
			self.assertEqual(buf.getvalue(), encoded)


class TestCRCIOWrapper(unittest.TestCase):

	def testEmptyStream(self):
		buf = io.BytesIO()
		stream = util.CRCIOWrapper(buf)
		self.assertEqual(stream.crc32, 0)

	def testProgressiveReads(self):
		"""
		The CRC32 is updated as reads occur.
		"""
		buf = io.BytesIO(b'ab')
		stream = util.CRCIOWrapper(buf)

		self.assertEqual(stream.read(1), b'a')
		self.assertEqual(stream.crc32, crc32(b'a'))

		self.assertEqual(stream.read(1), b'b')
		self.assertEqual(stream.crc32, crc32(b'ab'))

	def testProgressiveWrites(self):
		"""
		The CRC32 is updated as writes occur.
		"""
		buf = io.BytesIO()
		stream = util.CRCIOWrapper(buf)

		stream.write(b'a')
		self.assertEqual(stream.crc32, crc32(b'a'))

		stream.write(b'b')
		self.assertEqual(stream.crc32, crc32(b'ab'))

		self.assertEqual(stream.getvalue(), b'ab')

	def testSeekingProhibited(self):
		"""
		Seeking is not allowed.
		"""
		buf = io.BytesIO(b'abc')
		stream = util.CRCIOWrapper(buf)

		self.assertRaises(io.UnsupportedOperation, stream.seek, 0)

	def testTruncateToCurrentPos(self):
		"""
		Truncating to the current position is allowed.
		"""
		buf = io.BytesIO()
		stream = util.CRCIOWrapper(buf)
		stream.write(b'abc')

		stream.truncate()

		self.assertEqual(stream.getvalue(), b'abc')
		self.assertEqual(stream.crc32, crc32(b'abc'))

	def testTruncateToZero(self):
		"""
		Truncating to zero is allowed.
		"""
		buf = io.BytesIO()
		stream = util.CRCIOWrapper(buf)
		stream.write(b'abc')

		stream.truncate(0)

		self.assertEqual(stream.getvalue(), b'')
		self.assertEqual(stream.crc32, 0)

	def testTruncateToNonZero(self):
		"""
		Truncating to any other length is prohibited.
		"""
		buf = io.BytesIO()
		stream = util.CRCIOWrapper(buf)
		stream.write(b'abc')

		self.assertRaises(io.UnsupportedOperation, stream.truncate, 5)


if __name__ == "__main__":
	unittest.main()
