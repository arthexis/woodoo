import re
import threading
from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class Context:
    stack = threading.local()

    def __init__(self, data):
        self.data = data

    def __enter__(self):
        if not hasattr(self.stack, 'data'):
            self.stack.data = []
        self.stack.data.append(self.data)
        return self

    def __exit__(self, type, value, traceback):
        self.stack.data.pop()


class Sigil(str):
    def __mod__(self, other):
        if not hasattr(Context.stack, 'data') or not Context.stack.data:
            raise ValueError("No context available for formatting")
        
        context_data = Context.stack.data[-1]

        # If other is a string, treat it as a key into the current context data
        if isinstance(other, str):
            other = context_data.get(other)

        # Merge the data from the current Context and the interpolation target
        if isinstance(other, dict):
            data = {**context_data, **other}
        else:
            data = context_data
        
        try:
            # Extract the keys from the Sigil string
            keys = re.findall(r'%\[(.*?)\]', self)
            paths = [key.split('.') for key in keys]

            # Flatten only the required paths in the data
            flat_dict = {}
            for path in paths:
                obj = data
                for key in path:
                    if isinstance(obj, dict):
                        obj = obj.get(key)
                    elif hasattr(obj, '__dict__'):
                        obj = getattr(obj, key, None)
                    elif isinstance(obj, (list, tuple)) and key.isdigit():
                        obj = obj[int(key)]
                    else:
                        obj = None
                flat_dict['.'.join(path)] = obj

            # Replace square brackets with nested dots using a regular expression
            modified_str = re.sub(r'%\[(.*?)\]', 
                                   lambda match: '%' + '(' + match.group(1).replace('][', '.') + ')s', self)
            
            # Perform string formatting on the modified string
            return modified_str % flat_dict
        except (KeyError, AttributeError):
            return self

    def __iter__(self):
        # Split the string into text and sigil parts
        parts = re.split(r'(%\[[^\]]+\])', self)

        # Wrap the parts that contain sigils in Sigil()
        for part in parts:
            if '%[' in part and ']' in part:
                yield Sigil(part)
            else:
                yield part


class SigilFieldMixin:
    def __init__(self, string=fields.Default, **kwargs):
        super().__init__(string=string, **kwargs)
        self.help = kwargs.get('help', '') + " You can use %[] Sigils in this field."

    def convert_to_read(self, value, record, use_name_get=True):
        if isinstance(record, models.BaseModel):
            # Use the record's fields as the Context data
            data = record.read()[0]
            return Sigil(value) % data if value else super().convert_to_read(value, record, use_name_get)
        else:
            # Handle the case where record is not an Odoo model instance
            _logger.warning("SigilFieldMixin: record %s is not an Odoo model instance", record)
            return value

class SigilChar(SigilFieldMixin, fields.Char):
    pass


class SigilText(SigilFieldMixin, fields.Text):
    pass

