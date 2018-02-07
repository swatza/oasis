$(document).ready(function(){
	setInterval(function(){
            var currentdate = new Date();
            //$.getJSON("http://iriss4.ddns.net:9501/status", function(result){
            $.getJSON(document.getElementById("jsonAddr").innerHTML, function(result){    
                $("#statusmsg").html(result["status"]);
                $("#aclat").html(result["lat"]);
                $("#aclon").html(result["lon"]);
                $("#acalt").html(result["alt"]);
                $("#acrelalt").html(result["relAlt"]);
                $("#acvolt").html(result["acvolt"]);
                $("#accurr").html(result["accurr"]);
                $("#t1").html(result["t1"]);
                $("#rh").html(result["RH"]);
                $("#pres").html(result["pres"]);
                $("#acheading").html(result["acheading"]);
                $("#acairspd").html(result["acairspd"]);
                $("#acgndspd").html(result["acgndspd"]);
                $("#barAlt").html(result["barAlt"]);
                $("#DEG").html(result["DEG"]);
                $("#speed").html(result["speed"]);
                $("#statusmsg").html("Got Message" + "-" + currentdate.getMonth() + "/"
                + (currentdate.getDate()+1)  + "/" 
                + currentdate.getFullYear() + " @ "  
                + currentdate.getHours() + ":"  
                + currentdate.getMinutes() + ":" 
                + currentdate.getSeconds());
                $("#loading").html("")
            
		})
			.fail( function() {
				$("#statusmsg").html("Not running");


			});
	}, 2000);
});
