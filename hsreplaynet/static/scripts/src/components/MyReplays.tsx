import * as React from "react";
import {GameReplay, CardArtProps, ImageProps, GlobalGamePlayer} from "../interfaces";
import GameHistorySearch from "./GameHistorySearch";
import GameHistoryModeFilter from "./GameHistoryModeFilter";
import GameHistoryFormatFilter from "./GameHistoryFormatFilter"
import GameHistoryList from "./GameHistoryList";
import Pager from "./Pager";
import {parseQuery, toQueryString} from "../QueryParser"
import {formatMatch, modeMatch, nameMatch} from "../GameFilters"


interface MyReplaysProps extends ImageProps, CardArtProps, React.ClassAttributes<MyReplays> {
	username: string;
}

interface MyReplaysState {
	working?: boolean;
	queryMap?: Map<string, string>;
	games?: GameReplay[];
	count?: number;
	next?: string,
	previous?: string,
}

export default class MyReplays extends React.Component<MyReplaysProps, MyReplaysState> {

	constructor(props: MyReplaysProps, context: any) {
		super(props, context);
		this.state = {
			working: true,
			queryMap: parseQuery(document.location.hash.substr(1)),
			games: [],
			count: 0,
			next: null,
			previous: null,
		};
		this.query("/api/v1/games/");
	}

	protected query(url: string) {
		this.setState({
			working: true,
			games: [],
		});
		$.getJSON(url, {username: this.props.username}, (data) => {
			let games = [];
			if (data.count) {
				games = data.results;
			}
			this.setState({
				working: false,
				games: games,
				count: data.count,
				next: data.next,
				previous: data.previous,
			});
		});
	}

	componentDidUpdate(prevProps: MyReplaysProps, prevState: MyReplaysState, prevContext: any): void {
		location.replace("#" + toQueryString(this.state.queryMap));
	}

	render(): JSX.Element {
		let games = this.state.games;
		if (this.state.queryMap.size > 0) {
			var name = this.state.queryMap.get("name");
			var mode = this.state.queryMap.get("mode");
			var format = this.state.queryMap.get("format");
			games = games.filter(game => {
				if(name && !nameMatch(game, name.toLowerCase())) {
					return false;
				}
				if(mode && !modeMatch(game, mode)) {
					return false;
				}
				if(format && !formatMatch(game, format, mode)) {
					return false;
				}
				return true;
			});
		}

		let content = null;
		if (games.length) {
			content =  <GameHistoryList
				image={this.props.image}
				cardArt={this.props.cardArt}
				games={games}
			/>;
		}
		else {
			let message = null;
			if (this.state.working) {
				message = <p>Loading replays…</p>;
			}
			else {
				message = <div>
					<h2>No replay found</h2>
					{!!this.state.queryMap ? <p>
						<a href="#"
						   onClick={(e) => {e.preventDefault(); this.setState({queryMap: new Map<string, string>()})}}>Reset search</a>
					</p> : null}
				</div>;
			}
			content = <div className="list-message">{message}</div>;
		}

		let next = this.state.next && !this.state.working ? () => {
			this.query(this.state.next);
		} : null;

		let previous = this.state.previous && !this.state.working ? () => {
			this.query(this.state.previous);
		} : null;

		return (
			<div>
				<div className="row" id="replay-search">
					<div className="col-md-12 col-sm-12 col-xs-12 text-right">
						<br className="visible-xs-inline"/>
						<Pager next={next} previous={previous}/>
					</div>
					<div className="col-md-3 col-sm-4 col-xs-12">
						<GameHistorySearch
							query={this.state.queryMap.get("name")}
							setQuery={(value: string) => this.setState({queryMap: this.state.queryMap.set("name", value)})}
						/>
					</div>
					<div className="col-md-3 col-sm-4 col-xs-12">
						<GameHistoryModeFilter
							selected={this.state.queryMap.get("mode")}
							setQuery={(value: string) => this.setState({queryMap: this.state.queryMap.set("mode", value)})}
						/>
					</div>
					<div className="col-md-3 col-sm-4 col-xs-12">
						<GameHistoryFormatFilter
							selected={this.state.queryMap.get("format")}
							setQuery={(value: string) => this.setState({queryMap: this.state.queryMap.set("format", value)})}
						/>
					</div>
				</div>
				<div className="clearfix"/>
				{content}
				<div className="pull-right">
					<Pager next={next} previous={previous}/>
				</div>
			</div>
		);
	}
}
