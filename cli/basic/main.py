from cmd import Cmd


class MyCli(Cmd):
    intro = 'My simple CLI'
    prompt = '> '

    def __init__(self, **kwargs):
        super().__init__(self, **kwargs)
        self.name = ''
        self.index = 0

    def do_quit(self, cmd_arg):
        self.stdout.write('Bye !!!\n')
        raise SystemExit

    def do_inc(self, cmd_arg):
        self.index += 1

    def help_inc(self):
        self.stdout.write('increase index\n')

    def do_dec(self, cmd_arg):
        self.index -= 1

    def help_dec(self):
        self.stdout.write('decrease index\n')

    def do_view(self, cmd_arg):
        self.stdout.write('%s\n' % self.index)

    def help_view(self):
        self.stdout.write('view index value\n')

    def do_name(self, cmd_arg):
        if cmd_arg:
            self.name = str(cmd_arg)
            self.stdout.write('name set to "%s"\n' % self.name)
        else:
            self.stdout.write('name value is "%s"\n' % self.name)

    def help_name(self):
        self.stdout.write('read or write the name value\n\n' \
                          'read syntax: name\nwrite syntax: name [value]\n')

    def emptyline(self):
        # Override for empty lines do nothing (default repeat previous cmd).
        pass


if __name__ == '__main__':
    try:
        cli = MyCli()
        cli.cmdloop()
    except KeyboardInterrupt:
        pass
