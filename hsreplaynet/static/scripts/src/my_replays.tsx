import * as React from "react";
import * as ReactDOM from "react-dom";
import {image, cardArt} from "./helpers";
import MyReplays from "./components/MyReplays";


ReactDOM.render(
	<MyReplays
		image={image}
		cardArt={cardArt}
	/>,
	document.getElementById("my-games-container")
);
