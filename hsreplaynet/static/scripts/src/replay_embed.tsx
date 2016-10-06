import * as React from "react";
import JoustEmbedder from "./JoustEmbedder";


// Joust
let embedder = new JoustEmbedder();

var container = document.getElementById("joust-container");
if (container.hasAttribute("data-locale")) {
	embedder.locale = container.getAttribute("data-locale");
}

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

embedder.embed(container);
