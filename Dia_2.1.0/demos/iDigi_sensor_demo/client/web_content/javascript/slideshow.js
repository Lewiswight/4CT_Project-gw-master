	window.current = 0
	function update_content(location){

	 // random number forces IE not to cache demo.py content
	   new Ajax.Updater('content',location, {  method: 'get',
	      parameters: { width: $('content').scrollWidth, rand: Math.random()*11111	},
	   evalScripts: true } );
	}

	function nnext(){
		$('forward').blur();
		borders_off();
		   window.current= (window.current+1)%7 ;
		   update_content( "/"+window.current );
		   border_on(window.current)

	}
	function nback(){
		$('backward').blur();
		borders_off();
	   window.current=window.current-1;
	   if(window.current==-1){
	       window.current=6;
	   }
	   update_content( "/"+window.current );
	   border_on(window.current)
    }
	function setClass(classname, obj){
		if(obj && classname){
			obj.className = classname
		}
	}
	function borders_off(){
		d = document.getElementsByTagName("img");
		for(i = 0; i < 7;i++){
			setClass("borders_off",$(""+i));
		}
	}
	function border_on(obj){
		borders_off();
		setClass("borders_on",$(""+obj));
	}
