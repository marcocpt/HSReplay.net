import * as React from "react";
import * as ReactDOM from "react-dom";
import ShareGameDialog from "./components/ShareGameDialog";
import JoustEmbedder from "./JoustEmbedder";


let embedder = new JoustEmbedder();

// shared url decoding
if (location.hash) {
	var ret = location.hash.match(/turn=(\d+)(a|b)/);
	if (ret) {
		embedder.turn = ((+ret[1]) * 2) + (+(ret[2] == "b")) - 1;
	}
	ret = location.hash.match(/reveal=(0|1)/);
	if (ret) {
		embedder.reveal = (+ret[1] === 1);
	}
	ret = location.hash.match(/swap=(0|1)/);
	if (ret) {
		embedder.swap = (+ret[1] === 1);
	}
}

embedder.embed(
	document.getElementById("joust-container")
);

function renderShareDialog() {
	ReactDOM.render(
		<ShareGameDialog
			url={$("#share-game-dialog").data("url")}
			showLinkToTurn={true}
			showPreservePerspective={false}
			turn={embedder.turn}
			reveal={embedder.reveal}
			swap={embedder.swap}
		/>,
		document.getElementById("share-game-dialog")
	);
}

renderShareDialog();
embedder.on("turn", renderShareDialog);
embedder.on("reveal", renderShareDialog);
embedder.on("swap", renderShareDialog);
