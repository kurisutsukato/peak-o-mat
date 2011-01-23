env = Environment()

code = env.Dir('peak_o_mat')
script = env.File('peak-o-mat.py')
data = [env.Dir('data'), env.File('example.lpj')]
docs = [env.File('DOCUMENTATION'), env.File('CHANGELOG')]


posix():
    env.Install('/usr/local/bin', script)
    env.Install('/usr/local/lib/peak-o-mat', [code,data,docs])
    env.Alias('install', ['/usr/local/bin', '/usr/local/lib/peak-o-mat'])


posix()

    
