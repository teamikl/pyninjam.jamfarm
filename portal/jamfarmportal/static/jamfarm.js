
function get_status(server, node)
{
  $.getJSON("/server/status/"+server, function(data){
    var get_n = function(n){ return node.children('td:nth-child('+n+')') }
  
    if (data.error) {
      get_n(2).text(data.error)
    }
    else {
      var uinfo = $("<ul></ul>")
      $.each(data.userinfo, function(nick,channels){
        uinfo.append("<li>"+nick+"</li>")
      })
      get_n(2).text("")
      get_n(3).text(data.bpi + "/" + data.bpm)
      get_n(4).append(uinfo)
      get_n(5).text(data.topic)
    }
  })
}
