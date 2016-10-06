"use strict";

const path = require("path");
const webpack = require("webpack");
const BundleTracker = require("webpack-bundle-tracker");
const fs = require("fs");
const spawnSync = require("child_process").spawnSync;
const url = require("url");
const _ = require("lodash");


const exportSettings = [
	"STATIC_URL",
	"JOUST_STATIC_URL",
	"HEARTHSTONE_ART_URL",
	"JOUST_RAVEN_DSN_PUBLIC",
	"JOUST_RAVEN_ENVIRONMENT",
	"HEARTHSTONEJSON_URL",
];
const influxKey = "INFLUX_DATABASES";
const python = process.env.PYTHON || "python";
const manageCmd = [path.resolve(__dirname, "./manage.py"), "show_settings"];
const exportedSettings = JSON.parse(
	spawnSync(python, manageCmd.concat(exportSettings, [influxKey]), {encoding: "utf-8"}).stdout
);

const db = exportedSettings[influxKey] ? exportedSettings[influxKey]["joust"] : undefined;
const settings = exportSettings.reduce((obj, current) => {
	obj[current] = JSON.stringify(exportedSettings[current]);
	return obj;
}, {
	INFLUX_DATABASE_JOUST: db ? JSON.stringify(url.format({
		protocol: db.SSL ? "https" : "http",
		hostname: db.HOST,
		port: "" + db.PORT || 8086,
		pathname: "/write",
		query: {
			db: db.NAME,
			u: db.USER,
			p: db.PASSWORD,
			precision: "s",
		}
	})) : undefined
});

module.exports = {
	context: __dirname,
	entry: {
		my_replays: path.resolve(__dirname, "./hsreplaynet/static/scripts/src/my_replays"),
		replay_detail: path.resolve(__dirname, "./hsreplaynet/static/scripts/src/replay_detail"),
		replay_embed: path.resolve(__dirname, "./hsreplaynet/static/scripts/src/replay_embed"),
	},
	output: {
		path: path.resolve(__dirname, "./hsreplaynet/static/bundles/"),
		filename: "[name].js",
	},
	resolve: {
		modulesDirectories: ["node_modules"],
		extensions: ["", ".js", ".jsx", ".d.ts", ".ts", ".tsx"],
	},
	module: {
		loaders: [
			{
				test: /\.tsx?$/,
				loaders: [
					"babel-loader?presets[]=react&presets[]=es2015",
					"ts-loader",
				],
			}
		],
	},
	externals: {
		"react": "React",
		"react-dom": "ReactDOM",
		"jquery": "jQuery",
		"joust": "Joust",
	},
	plugins: [
		new BundleTracker({path: __dirname, filename: "./build/webpack-stats.json"}),
		new webpack.DefinePlugin(settings),
	],
	watchOptions: {
		// required in the Vagrant setup due to Vagrant inotify not working
		poll: true
	},
};
