import json

# class for functions that should be available across all entities in our solution.
class EntityBase:

    def check_type(self, entity):
        if type(entity) != self:
            raise Exception(f'provided object was {type(entity)} and not {type(self)}')
        else:
            return True

    def to_json(self):
        res = json.dumps(self)
        return res

