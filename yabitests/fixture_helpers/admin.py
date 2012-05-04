'''
Module providing helper methods for creating data in yabi admin from tests
'''

def create_tool(name, display_name=None, path=None, backend_name='Local Execution', fs_backend_name='Local Filesystem'):
    from yabiadmin.yabi import models
    if display_name is None: display_name = name
    if path is None: path = name
    lfs = models.Backend.objects.get(name=fs_backend_name)
    lex = models.Backend.objects.get(name=backend_name)
    hostname = models.Tool.objects.create(name=name, display_name=display_name, path=path, backend=lex, fs_backend=lfs)

def add_tool_to_all_tools(toolname):
    from yabiadmin.yabi import models
    tool = models.Tool.objects.get(name=toolname)
    tg = models.ToolGroup.objects.get(name='select data')
    alltools = models.ToolSet.objects.get(name='alltools')
    tg.toolgrouping_set.create(tool=tool, tool_set=alltools)

def create_exploding_backend():
    from yabiadmin.yabi import models
    exploding_backend = models.Backend.objects.create(name='Exploding Backend', scheme='explode', hostname='localhost.localdomain', path='/', submission='${command}\n')
    null_credential = models.Credential.objects.get(description='null credential')
    models.BackendCredential.objects.create(backend=exploding_backend, credential=null_credential, homedir='')

def create_backend(scheme="ssh", hostname="localhost.localdomain",path="/",submission="${command}"):
    from yabiadmin.yabi import models
    backend = models.Backend.objects.create(name='Test %s Backend'%scheme.upper(), scheme=scheme, hostname=hostname, path=path, submission=submission)
    # continue this...
    
def create_localfs_backend(scheme="localfs", hostname="localhost.localdomain", path="/tmp/yabi-localfs-test/"):
    from yabiadmin.yabi import models
    backend = models.Backend.objects.create(
        name='Test %s Backend'%scheme.upper(),
        description="Test %s Backend"%scheme.upper(),
        scheme=scheme, 
        hostname=hostname,
        port=None,
        path=path, 
        submission=""
    )
    cred = models.Credential.objects.create( 
        description='Test %s Credential'%scheme.upper(), 
        username='username',
        password='password',
        cert='cert',
        key='key',
        user=models.User.objects.get(name="demo")
    )
    
    #join them
    backend_cred = models.BackendCredential.objects.create(
        backend = backend,
        credential = cred,
        homedir = "",
        visible = True,
        default_stageout = False,
        submission = ""
    )
    import os
    try:
        os.mkdir("/tmp/yabi-localfs-test/")
    except OSError, ose:
        if ose.errno != 17:
            raise
        #directory already exists... leave it
    
def destroy_localfs_backend(scheme="localfs", hostname="localhost.localdomain", path="/tmp/yabi-localfs-test/"):
    from yabiadmin.yabi import models
    backend = models.Backend.objects.filter(
        name='Test %s Backend'%scheme.upper(),
        description="Test %s Backend"%scheme.upper(),
        scheme=scheme, 
        hostname=hostname,
        port=None,
        path=path, 
        submission=""
    ).delete()
    cred = models.Credential.objects.filter( 
        description='Test %s Credential'%scheme.upper(), 
        username='username',
        password='password',
        cert='cert',
        key='key',
        user=models.User.objects.get(name="demo")
    ).delete()
    
    #join them
    backend_cred = models.BackendCredential.objects.filter(
        backend = backend,
        credential = cred,
        homedir = "",
        visible = True,
        default_stageout = False,
        submission = ""
    ).delete()
    import shutil
    shutil.rmtree("/tmp/yabi-localfs-test/")    
    
def create_fakes3_backend(scheme="s3", hostname="localhost.localdomain", path="/" ):
    from yabiadmin.yabi import models
    backend = models.Backend.objects.create(
        name='Test %s Backend'%scheme.upper(),
        description="Test %s Backend"%scheme.upper(),
        scheme=scheme, 
        hostname=hostname,
        port=8080,
        path=path, 
        submission=""
    )
    cred = models.Credential.objects.create( 
        description='Test %s Credential'%scheme.upper(), 
        username='username',
        password='password',
        cert='cert',
        key='key',
        user=models.User.objects.get(name="demo")
    )
    
    #join them
    backend_cred = models.BackendCredential.objects.create(
        backend = backend,
        credential = cred,
        homedir = "",
        visible = True,
        default_stageout = False,
        submission = ""
    )
        

def create_tool_cksum():
    from yabiadmin.yabi import models
    create_tool('cksum')
    add_tool_to_all_tools('cksum')
    tool = models.Tool.objects.get(name='cksum')
    tool.accepts_input = True
    star_extension = models.FileExtension.objects.get(pattern='*')
    models.ToolOutputExtension.objects.create(tool=tool, file_extension=star_extension)

    value_only = models.ParameterSwitchUse.objects.get(display_text='valueOnly')

    tool_param = models.ToolParameter.objects.create(tool=tool, switch_use=value_only, mandatory=True, rank=99, file_assignment = 'all', switch='files')
    all_files = models.FileType.objects.get(name='all files')
    tool_param.accepted_filetypes.add(all_files)

    tool.save()

def create_tool_dd():
    from yabiadmin.yabi import models
    create_tool('dd')
    add_tool_to_all_tools('dd')
    tool = models.Tool.objects.get(name='dd')
    tool.accepts_input = True
    star_extension = models.FileExtension.objects.get(pattern='*')
    models.ToolOutputExtension.objects.create(tool=tool, file_extension=star_extension)

    combined_eq = models.ParameterSwitchUse.objects.get(display_text='combined with equals')

    if_tool_param = models.ToolParameter.objects.create(tool=tool, switch_use=combined_eq, mandatory=True, rank=1, file_assignment = 'batch', switch='if')
    all_files = models.FileType.objects.get(name='all files')
    if_tool_param.accepted_filetypes.add(all_files)

    of_tool_param = models.ToolParameter.objects.create(tool=tool, switch_use=combined_eq, mandatory=True, rank=2, file_assignment = 'none', switch='of', output_file=True)

    tool.save()


