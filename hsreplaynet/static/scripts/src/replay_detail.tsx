import * as React from "react";
import * as ReactDOM from "react-dom";
import ShareGameDialog from "./components/ShareGameDialog";
import JoustEmbedder from "./JoustEmbedder";
import MetricsReporter from "./metrics/MetricsReporter";
import BatchingMiddleware from "./metrics/BatchingMiddleware";
import InfluxMetricsBackend from "./metrics/InfluxMetricsBackend";


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

// share dialog
let metrics: MetricsReporter = null;
let endpoint = INFLUX_DATABASE_JOUST;
if (endpoint) {
	metrics = new MetricsReporter(
		new BatchingMiddleware(new InfluxMetricsBackend(endpoint)),
		(series: string): string => "hsreplaynet_" + series
	);
}
let shared = {};

function renderShareDialog() {
	ReactDOM.render(
		<ShareGameDialog
			url={$("#share-game-dialog").data("url")}
			showLinkToTurn={true}
			showPreservePerspective={false}
			turn={embedder.turn}
			reveal={embedder.reveal}
			swap={embedder.swap}
			onShare={(network: string, linkToTurn: boolean) => {
				if (!metrics) {
					return;
				}
				if (shared[network]) {
					// deduplicate
					return;
				}
				metrics.writePoint("shares", {count: 1, link_to_turn: linkToTurn}, {network: network});
				shared[network] = true;
			}}
		/>,
		document.getElementById("share-game-dialog")
	);
}

renderShareDialog();
embedder.on("turn", renderShareDialog);
embedder.on("reveal", renderShareDialog);
embedder.on("swap", renderShareDialog);
