import * as React from "react";

interface GameHistoryModeFilterProps extends React.ClassAttributes<GameHistoryModeFilterState > {
	setQuery: (type: string) => void;
	selected: string;
}

interface GameHistoryModeFilterState {
}

export default class GameHistoryModeFilter extends React.Component<GameHistoryModeFilterProps, GameHistoryModeFilterState> {

	render(): JSX.Element {
		if (!this.props.selected) {
			this.props.selected = "";
		}
		return (
			<div>
				<select className="form-control" onChange={(e: any) => this.props.setQuery(e.target.value)} value={this.props.selected}>
					<option value="">All Modes</option>
					<option value="arena">Arena</option>
					<option value="ranked">Ranked</option>
					<option value="casual">Casual</option>
					<option value="brawl">Tavern Brawl</option>
					<option value="friendly">Friendly</option>
					<option value="adventure">Adventure</option>
				</select>
			</div>
		);
	}
}
