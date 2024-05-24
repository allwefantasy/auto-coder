
def multi_turn(func,*args,**kwargs):
    conversation = []
    func.prompt(args,kwargs)