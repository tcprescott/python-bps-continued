#!/usr/bin/python3
import unittest
from io import BytesIO
from blip.apply import apply_to_bytearrays
from blip.io import read_blip
from blip.validate import check_stream
from blip.test.util import find_blip

class TestApplyToByteArrays(unittest.TestCase):

	def _run_test(self, patchname, source):
		raw_patch = find_blip(patchname)
		iterable = check_stream(read_blip(BytesIO(raw_patch)))

		magic, sourceSize, targetSize, metadata = next(iterable)

		assert len(source) == sourceSize

		target = bytearray(targetSize)

		apply_to_bytearrays(iterable, source, target)

		return target

	def testIgnoresHeader(self):
		"""
		apply_to_bytearrays shouldn't crash if it gets a header opcode.
		"""
		raw_patch = find_blip("sourceread")
		iterable = read_blip(BytesIO(raw_patch))

		# I happen to know this particular patch has sourcesize and
		# targetsize equal to 1.
		target = bytearray(1)
		apply_to_bytearrays(iterable, b'A', target)

		self.assertSequenceEqual(target, b'A')

	def testEmptyPatch(self):
		"""
		The simplest possible patch can be processed correctly.
		"""
		target = self._run_test("empty", b'')

		self.assertSequenceEqual(b'', target)

	def testPatchWithSourceRead(self):
		"""
		We can process a patch with a SourceRead opcode.
		"""
		target = self._run_test("sourceread", b'A')

		self.assertSequenceEqual(b'A', target)

	def testPatchWithTargetRead(self):
		"""
		We can process a patch with a TargetRead opcode.
		"""
		target = self._run_test("targetread", b'')

		self.assertSequenceEqual(b'A', target)

	def testPatchWithSourceCopy(self):
		"""
		We can process a patch with a SourceCopy opcode.
		"""
		target = self._run_test("sourcecopy", b'AB')

		self.assertSequenceEqual(b'BA', target)

	def testPatchWithTargetCopy(self):
		"""
		We can process a patch with a TargetCopy opcode.
		"""
		target = self._run_test("targetcopy", b'')

		self.assertSequenceEqual(b'AAA', target)

if __name__ == "__main__":
	unittest.main()
