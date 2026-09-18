class solution:
    def twosum(self, nums, target):
        seen = {}

        for i in nums:
            x = nums[i]
            need = target - x

            if need in seen:
                return [seen[need], i]

            seen[x] = i
