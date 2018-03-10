var app = new Vue({
    el: '#active-conference',
    data: {
        loggedUser: "slogan@twilio.com",
        syncEndpoint: "",
        syncStatus: "Disconnected",
        newParticipant: false,
        newParticipantNumber: '',
        conferenceParticipants: [],
        currentConferenceMap: "MPa390d0599a4a4be898f028305a95e3b6",
        previousConferences: [
            {
                confSid: "CF05u757673033006979",
                friendlyName: "StusConference",
                participants: ["+447475737643", "+447475863519"],
                duration: 500
            },
            {
                confSid: "CF75849304958634",
                friendlyName: "StusConference",
                participants: ["+447475737643", "+447475863523"],
                duration: 300
            }
        ],
    },
    methods: {
        syncRetrieveConferenceMap: function(data) {
            console.log("syncRetrieveConferenceMap RUNNING");
            console.log("data >>>  ");
            console.log(data);
            console.log(data.items[0].descriptor.data);
            var self = this;
            var participant = {};
            for (let i = 0; i < data.items.length; i++) {
                participant['callSid'] = data.items[i].descriptor.data['callSid'];
                participant['participantNumber'] = data.items[i].descriptor.data['participantNumber'];
                participant['direction'] = data.items[i].descriptor.data['direction']
                participant['muted'] = data.items[i].descriptor.data['muted']
                participant['speaking'] = data.items[i].descriptor.data['speaking']
                participant['dropped'] = data.items[i].descriptor.data['dropped']
                self.conferenceParticipants.push(participant);
                console.log(participant);
            }
        },
        syncConferenceMap: function(data) {
            var self = this;
            var participant = {};
            console.log("DATA >>> ", data)
            participant['callSid'] = data.callSid;
            participant['participantNumber'] = data.participantNumber;
            participant['direction'] = data.direction;
            participant['muted'] = data.muted;
            participant['speaking'] = data.speaking;
            participant['dropped'] = data.dropped;
            self.conferenceParticipants.push(participant);
        },
        syncConferenceParticipant: function(data) {
            var self = this;
            var participant = {};
            console.log("SYNCHING PARTICIPANT >>> ", data.participantNumber);
            for(var i in self.conferenceParticipants ) {
                console.log(i.participantNumber);
                if (self.conferenceParticipants[i].participantNumber == data.participantNumber) {
                    console.log(self.conferenceParticipants[i]);
                    self.conferenceParticipants[i].muted = data.muted;
                    self.conferenceParticipants[i].speaking = data.speaking;
                    self.conferenceParticipants[i].dropped = data.dropped;
                }
            }

        },
        removeConferenceParticipant: function(data) {
            var self = this;
            console.log("TRYING TO REMOVE PARTICIPANTS (probably failing)... ")
            console.log(self)
            for (var i in self.conferenceParticipants) {
                console.log(i);
                if (self.conferenceParticipants[i].callSid == data) {
                    console.log(self.conferenceParticipants[i]);
                    self.conferenceParticipants.splice(i, 1);
                }
            }
        },
        muteParticipant: function(index) {
            console.log(this.conferenceParticipants[index].callSid);
            muteOn = !this.conferenceParticipants[index].muted;
            participant = this.conferenceParticipants[index].callSid;
            payload = {
                muteOn: muteOn,
                participant: participant
            };
            axios.post('/mute', payload).
            then(function(response) {
                console.log(response);
                console.log('Mute successful!');
            });
            
        },
        dialParticipant: function() {
            vm = this;
            console.log(vm)
            const payload = {
                number: vm.newParticipantNumber
            };
            console.log(payload);
            axios.post('/dial', payload).
            then(function(response) {
                console.log(response);
                vm.newParticipant = false;
                vm.participantNumber = '';
            });
        }
    }
})

// Twilio Sync setup
var syncClient;
var syncMapName = "ActiveConference";
var userid = app.$data.loggedUser;
var ts = Math.round((new Date().getTime() / 1000));
var tokenUserId = userid + ts;
app.$data.syncEndpoint = tokenUserId;
$.getJSON('/token?identity=' + tokenUserId, function (tokenResponse) {
    //Initialise sync client
    var syncClient = new Twilio.Sync.Client(tokenResponse.token, { logLevel: 'info' });
    app.$data.syncStatus = userid + ' Connected';
    //subscribe to map
    syncClient.map(syncMapName).then(function(map) {
        map.getItems().then(function(items) {
            app.syncRetrieveConferenceMap(items);
        })
        .catch(function(error) {
            console.error('Map getItems() failed', error);
        });
   
        console.log("Dashboard Ready!");
        map.on('itemAdded', function(item) {
            console.log('New Participant: ', item)
            app.syncConferenceMap(item.descriptor.data);
        });

        map.on('itemUpdated', function(item) {
            console.log('PARTICIPANT UPDATE >>> ', item)
            app.syncConferenceParticipant(item.descriptor.data);
        });

        map.on('itemRemoved', function(item) {
            console.log(item);
            app.removeConferenceParticipant(item)
        });
    });
})

$('.ui.accordion')
  .accordion()
;
