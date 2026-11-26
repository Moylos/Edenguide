try:
    import python_multipart
    print('ok', getattr(python_multipart,'__version__','?'))
except Exception as e:
    print('no', e)
try:
    import multipart
    print('ok2', getattr(multipart,'__version__','?'))
except Exception as e:
    print('no2', e)
