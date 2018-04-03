
var app = new Vue({
    el: '#active-conference',
    data: {
        loggedUser: currentUserEmail,
        syncEndpoint: "",
        syncStatus: "Disconnected",
        newParticipant: false,
        newParticipantNumber: '',
        conferenceParticipants: [],
        currentConferenceMap: syncMapSid,
        currentConferenceSid: '',
        message: '',
        previousConferences: [{
            'name': 'The MArae',
            'dateCreated': 'Today',
            'participants': [{
                    'number': '1234'
                },
                {
                    'number': '5678'
                }]
        }]
    },
    methods: {
        syncRetrieveConferenceMap: function(data) {
            console.log("syncRetrieveConferenceMap RUNNING");
            console.log("data >>>  ");
            console.log(data);
            console.log(data.items[0].descriptor.data);
            var self = this;
            currentConferenceSid = data.items[0].descriptor.data.conferenceSid
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
            self.currentConferenceSid = data.conferenceSid
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
            conferenceSid = this.currentConferenceSid;
            payload = {
                muteOn: muteOn,
                participant: participant,
                conferenceSid: conferenceSid
            };
            axios.post('/mute', payload).
            then(function(response) {
                console.log(response);
                console.log('Mute successful!');
            });
            
        },
        dropParticipant: function(index) {
            console.log(this.conferenceParticipants[index].callSid);
            participant = this.conferenceParticipants[index].callSid;
            payload = {
                participant: participant
            };
            axios.post('/drop', payload).
            then(function(response) {
                console.log(response);

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
        },
        retrievePastConferences: function() {
            vm = this;
            axios('/previous_conferences').
            then(function(response) {
                console.log(response);
                vm.previousConferences = response.data;
            for (var i=0; i < vm.previousConferences.length; i++) {
                   var time = vm.previousConferences[i].dateCreated;
                   var moment_time = moment(time).format('LLLL');
                   vm.previousConferences[i].dateCreated = moment_time;
                   for (var p = 0; p < vm.previousConferences[i].participants.length; p++) {
                       var duration = parseInt(vm.previousConferences[i].participants[p].duration);
                       console.log(duration)
                       var formatted_duration = vm.SecondsTohhmmss(duration);
                       vm.previousConferences[i].participants[p].duration = formatted_duration;
                   }
                }
                

            });
        },
        SecondsTohhmmss : function(totalSeconds) {
            var hours   = Math.floor(totalSeconds / 3600);
            var minutes = Math.floor((totalSeconds - (hours * 3600)) / 60);
            var seconds = totalSeconds - (hours * 3600) - (minutes * 60);

            // round seconds
            seconds = Math.round(seconds * 100) / 100

            var result = (hours < 10 ? "0" + hours : hours);
                result += ":" + (minutes < 10 ? "0" + minutes : minutes);
                result += ":" + (seconds  < 10 ? "0" + seconds : seconds);
            return result;
        }
    },
    created: function() {
        this.retrievePastConferences();
    //     $('.ui.accordion').accordion('refresh');

    },
})

// Twilio Sync setup
var syncClient;
var syncMapName = "{{ current_user.email }}";
var userid = app.$data.loggedUser;
var ts = Math.round((new Date().getTime() / 1000));
var tokenUserId = userid + ts;
app.$data.syncEndpoint = tokenUserId;
$.getJSON('/auth/token?identity=' + tokenUserId, function (tokenResponse) {
    //Initialise sync client
    var syncClient = new Twilio.Sync.Client(tokenResponse.token, { logLevel: 'info' });
    app.$data.syncStatus = userid + ' Connected';
    //subscribe to map
    syncClient.map(app.currentConferenceMap).then(function(map) {
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
            app.removeConferenceParticipant(item);
            app.retrievePastConferences();
        });
    });
})

$('.ui.accordion')
  .accordion('debug: true')
;
