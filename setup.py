#!/usr/bin/python3
from distutils.core import setup

setup(
		name="python-blip",
		description="A toolkit for working with Blip patch files",
		author="Timothy Allen",
		author_email="screwtape@froup.com",
		packages=["blip"],
		scripts=[
			"bin/blip-apply",
			"bin/blip-asm",
			"bin/blip-disasm",
			"bin/blip-validate",
			],
	)
