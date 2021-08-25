#!/usr/bin/env python3

class MikrotikRangeExcludeModule(object):
	@staticmethod
	def mikrotik_range_exclude(exclusions, start, count):
		ids = set(range(start, start + count)) - set([int(i) + start for i in exclusions])
		result = ''
		for i in range(start, start + count):
			if i not in ids:
				pass
			elif i-1 not in ids:
				result += ',' + str(i)
			elif i+1 not in ids:
				result += '-' + str(i)
		return result[1:]

class FilterModule(object):
	def filters(self):
		return {
			'mikrotik_range_exclude': MikrotikRangeExcludeModule.mikrotik_range_exclude,
		}

def test_range_exclude(module):
	inputs = [
		((1,2,3), '0,4-99'),
		((), '0-99'),
		((2, 4, 6), '0-1,3,5,7-99'),
	]
	for inp in inputs:
		result = module.mikrotik_range_exclude(inp[0], 0, 100)
		print('RESULT: {}'.format(result))
		print('EXPECT: {}'.format(inp[-1]))
		assert result == inp[-1]

if __name__ == '__main__':
	module = MikrotikRangeExcludeModule
	test_range_exclude(module)
