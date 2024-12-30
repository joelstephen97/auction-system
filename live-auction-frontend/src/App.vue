<template>
  <div id="app">
    <h1>Live Auction System</h1>

    <div>
      <h2>Admin Panel</h2>
      <form @submit.prevent="registerAdmin">
        <h3>Register Admin</h3>
        <input v-model="admin.username" placeholder="Username" />
        <input v-model="admin.password" placeholder="Password" type="password" />
        <button type="submit">Register</button>
      </form>

      <form @submit.prevent="createAuction">
        <h3>Create Auction</h3>
        <input v-model="auction.name" placeholder="Item Name" />
        <input v-model="auction.description" placeholder="Description" />
        <input v-model.number="auction.starting_price" placeholder="Starting Price" type="number" />
        <button type="submit">Create Auction</button>
      </form>
    </div>

    <div>
      <h2>Available Auctions</h2>
      <button @click="fetchAuctions">Refresh Auctions</button>
      <ul>
        <li v-for="item in auctions" :key="item.id">
          {{ item.name }} (Current Price: {{ item.current_price }})
          <button @click="selectAuction(item.id)">Bid</button>
        </li>
      </ul>
    </div>

    <div v-if="selectedAuction">
      <h2>Bidding on: {{ selectedAuction.name }}</h2>
      <form @submit.prevent="placeBid">
        <input v-model.number="bidAmount" placeholder="Your Bid" type="number" />
        <input v-model="bidder" placeholder="Your Name" />
        <button type="submit">Place Bid</button>
      </form>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      admin: {
        username: '',
        password: ''
      },
      auction: {
        name: '',
        description: '',
        starting_price: 0
      },
      auctions: [],
      selectedAuction: null,
      bidAmount: 0,
      bidder: ''
    };
  },
  methods: {
    async registerAdmin() {
      try {
        const response = await axios.post('http://localhost:8000/admin/register/', this.admin);
        alert(response.data.detail);
      } catch (error) {
        alert(error.response.data.detail);
      }
    },
    async createAuction() {
      try {
        const response = await axios.post('http://localhost:8000/admin/auctions/', this.auction, {
          auth: {
            username: this.admin.username,
            password: this.admin.password
          }
        });
        alert('Auction Created: ' + response.data.name);
      } catch (error) {
        alert(error.response.data.detail);
      }
    },
    async fetchAuctions() {
      try {
        const response = await axios.get('http://localhost:8000/auctions/');
        this.auctions = response.data;
      } catch (error) {
        alert('Failed to fetch auctions');
      }
    },
    selectAuction(itemId) {
      this.selectedAuction = this.auctions.find(item => item.id === itemId);
    },
    async placeBid() {
      if (!this.selectedAuction) return;
      try {
        await axios.post(`http://localhost:8000/auctions/${this.selectedAuction.id}/bid`, {
          user: this.bidder,
          bid_amount: this.bidAmount
        });
        alert('Bid placed!');
        this.fetchAuctions(); // Refresh auctions after placing a bid
      } catch (error) {
        alert('Failed to place bid: ' + error.response.data.detail);
      }
    }
  }
};
</script>

<style>
#app {
  font-family: Arial, sans-serif;
  margin: 20px;
}
h1 {
  color: #333;
}
form {
  margin-bottom: 20px;
}
input {
  margin: 5px;
}
button {
  margin: 5px;
  padding: 5px 10px;
}
</style>
