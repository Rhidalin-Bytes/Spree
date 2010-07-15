# b3/plugins/spree.py
#
# This plugin will show killing or loosing spree messages.
#
# It's written with fun, for fun. Please report any errors or
# if something can be done more efficient to Walker@1stsop.nl
# 
# 07-15-2010, Rhidaling Bytes: Allow admin to spam a players spree
# 08-03-2005, Walker: Changed the end spree messages a bit. 
# 08-01-2005, ThorN:  Code change suggestions 
# 08-01-2005, Walker: Initial creation 
# 
# all plugins must import b3 and b3.events
import b3
import b3.events

class SpreeStats:
    kills                  = 0
    deaths                 = 0
    endLoosingSpreeMessage = None
    endKillSpreeMessage    = None
    
#--------------------------------------------------------------------------------------------------
class SpreePlugin(b3.plugin.Plugin):
    _adminPlugin = None
    _killingspree_messages_dict = {}
    _loosingspree_messages_dict = {}
    _reset_spree_stats = 0
    _min_level_spree_cmd = 0
    _clientvar_name = 'spree_info'
    
    def startup(self):
        """\
        Initialize plugin settings
        """

        self.debug('Starting')
        # get the plugin so we can register commands
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            # something is wrong, can't start without admin plugin
            self.error('Could not find admin plugin')
            return False

        # Get the settings from the config.
        if self.config.get('settings', 'reset_spree') == '1':
            self._reset_spree_stats = 1
        self._min_level_spree_cmd = self.config.getint('settings', 'min_level_spree_cmd')
        
        # register our !spree command
        self.verbose('Registering commands')
        self._adminPlugin.registerCommand(self, 'spree', self._min_level_spree_cmd, self.cmd_spree)

        # listen for client events
        self.verbose('Registering events')
        self.registerEvent(b3.events.EVT_CLIENT_KILL)
        self.registerEvent(b3.events.EVT_GAME_EXIT)

        # Initialize the message list used in this plugin
        self.init_spreemessage_list()

        self.debug('Started')

    def onLoadConfig(self):
        self.init_spreemessage_list()

    def handle(self, event):
        """\
        Handle intercepted events
        """
        if event.type == b3.events.EVT_CLIENT_KILL:
             self.handle_kills(event.client, event.target)
        elif event.type == b3.events.EVT_GAME_EXIT:
             if self._reset_spree_stats:
                for c in self.console.clients.getList():
                   self.init_spree_stats(c)
              
    def init_spreemessage_list(self):
        # Get the spree messages from the config
        # Split the start and end spree messages and save it in the dictionary
        for kills, message  in self.config.items('killingspree_messages'):
            # force the kills to an integer
            self._killingspree_messages_dict[int(kills)]  = message.split('#')
        
        for deaths, message in self.config.items('loosingspree_messages'):
            self._loosingspree_messages_dict[int(deaths)] = message.split('#')

        self.verbose('spree-messages are loaded in memory')

    def init_spree_stats(self, client):
        # initialize the clients spree stats
        client.setvar(self, self._clientvar_name, SpreeStats())
    
    def get_spree_stats(self, client):
        # get the clients stats
        # pass the plugin reference first
        # the key second
        # the defualt value first
        
        if not client.isvar(self, self._clientvar_name):
            # initialize the default spree object
            # we don't just use the client.var(...,default) here so we
            # don't create a new SpreeStats object for no reason every call
            client.setvar(self, self._clientvar_name, SpreeStats())
            
        return client.var(self, self._clientvar_name).value
    
    def handle_kills(self, client=None, victim=None):
        """\
        A kill was made. Add 1 to the client and set his deaths to 0.
        Add 1 death to the victim and set his kills to 0.
        """

        # client (attacker)
        if client:
            # we grab our SpreeStats object here
            # any changes to its values will be saved "automagically"
            spreeStats = self.get_spree_stats(client)
            spreeStats.kills += 1
            
            # Check if the client was on a loosing spree. If so then show his end loosing spree msg.
            if spreeStats.endLoosingSpreeMessage:
                self.show_message( client, victim, spreeStats.endLoosingSpreeMessage )
                # reset any possible loosing spree to None
                spreeStats.endLoosingSpreeMessage = None
            # Check if the client is on a killing spree. If so then show it.
            message = self.get_spree_message(spreeStats.kills, 0)
            if message:
                #Save the 'end'spree message in the client. That is used when the spree ends.
                spreeStats.endKillSpreeMessage = message[1]


                #Show the 'start'spree message
                self.show_message( client, victim, message[0] )

            # deaths spree is over, reset deaths
            spreeStats.deaths = 0

        # Victim
        if victim:
            spreeStats = self.get_spree_stats(victim)
            spreeStats.deaths += 1
            
            # Check if the victim had a killing spree and show a end_killing_spree message
            if spreeStats.endKillSpreeMessage:
                self.show_message( client, victim, spreeStats.endKillSpreeMessage )
                # reset any possible end spree to None
                spreeStats.endKillSpreeMessage = None

            #Check if the victim is on a 'loosing'spree
            message = self.get_spree_message(0, spreeStats.deaths)
            if message:
                #Save the 'loosing'spree message in the client.
                spreeStats.endLoosingSpreeMessage = message[1]
                
                self.show_message( victim, client, message[0] )
                
            # kill spree is over, reset kills
            spreeStats.kills = 0

    def get_spree_message(self, kills, deaths):
        """\
        Get the appropriate spree message.
        Return a list in the format (start spree message, end spree message)
        """
        
        # default is None, there is no message
        message = None
        
        # killing spree check
        if kills != 0:
            # if there is an entry for this number of kills, grab it, otherwise
            # return None
            message = self._killingspree_messages_dict.get(kills, None)
        
        # loosing spree check
        elif deaths != 0:
            message = self._loosingspree_messages_dict.get(deaths, None)
            
        return message

    def show_message(self, client, victim=None, message=None):
        """\
        Replace variables and display the message
        """
        if (message != None) and not (client.hide):
            message = message.replace('%player%',client.name)
            if victim:
                message = message.replace('%victim%',victim.name)
            self.console.say(message)        
    
    
    def cmd_spree(self, data, client, cmd=None):
        """\
        Show a players winning/loosing spree
        """
        targm = "^7You have"
        targmns = "^7Your\'re"
        m = self._adminPlugin.parseUserCmd(data)
        if m:
            sclient = self._adminPlugin.findClientPrompt(m[0], client)
            if sclient:
                spreeStats = self.get_spree_stats(sclient)
                self.debug('sclient = %s' % sclient.exactName)
                targm = ('%s has ' % sclient.exactName)
                targmns = ('%s is ' % sclient.exactName)
            else:
                return
        else:
            spreeStats = self.get_spree_stats(client)
            
        if spreeStats.kills > 0:
            cmd.sayLoudOrPM(client, '%s ^2%s^7 kills in a row' % targm, spreeStats.kills)
        elif spreeStats.deaths > 0:
            cmd.sayLoudOrPM(client, '%s ^1%s^7 deaths in a row' % targm, spreeStats.deaths)
        else:
            cmd.sayLoudOrPM(client, '%s not having a spree right now' % targmns)