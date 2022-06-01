
class Utils:
    @staticmethod
    def blocks_to_days(blocks):
        time = blocks * 13  # multiply the number of blocks by the average time it takes to mine a block
        ls = [(60, ' min'), (60, ' hours'), (24, ' days')]
        if time < 1000:
            return f'{"{0:.4g}".format(time)} seconds'
        for tpl in ls:
            time = time / tpl[0]
            if time < 100:
                return f'{"{0:.4g}".format(time)}{tpl[1]}'
        return f'{"{0:.4g}".format(time)}{ls[2][1]}'