/* This is just a snippet of some of my event-handling code in a browser.

You need reconnecting web socket:

https://github.com/joewalnes/reconnecting-websocket

*/

this.socket = new ReconnectingWebSocket('ws://server:5003/events');
this.socket.onmessage = function(evt) {

    data = JSON.parse(evt.data);
    if (data['sender'] == 'asterisk' &&
            data['event'] == 'incoming-call') {
	incoming_call(data);
    } else if (data['sender'] == 'weather') {
	weather_event(data);
    } else if (data['sender'] == 'garagedoor') {
        $('#garage').html(data['state'].toUpperCase());
    } else if (data['sender'] == 'lrmotion') {
        reload_mainimg();
    } else if (data['sender'] == 'mpd') {
	mpd_event(data);
    } else if (data['sender'] == 'aprs') {
	aprs_event(data);
    } else if (data['sender'] == 'wemo') {
	wemo_event(data);
    } else if (data['sender'] == 'hvac') {
	hvac_event(data);
    }
};
