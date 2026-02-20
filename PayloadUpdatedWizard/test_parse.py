import importlib, sys
sys.path.append(r'C:\Users\Saurabh\Downloads\PayloadUpdatedWizard')
mod = importlib.import_module('GeminiPayloadDiff_GeminiUltra_FIXED_optimized_FIXED')
cases = ['foo', "{'a':1}", 'None', 'true', '123', '  "quoted"  ', "{a:1}", "[1,2,3]", "{'x': 'y',}"]
for c in cases:
    obj, err = mod.parse_jsonish_verbose(c)
    print(repr(c), '->', 'obj=', repr(obj), 'err=', repr(err))
